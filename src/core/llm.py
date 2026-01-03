"""
DPOS LLM Provider Module
Unified LLM interface with provider abstraction, caching, and graceful degradation.
"""
from typing import Optional, Any, Dict, List, Callable, TypeVar
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import wraps
from enum import Enum
import hashlib
import json
import time
from datetime import datetime, UTC

from src.core.config import settings
from src.core.logging import get_logger
from src.core.resilience import CircuitBreaker, CircuitBreakerConfig, retry

logger = get_logger(__name__)

T = TypeVar('T')


class LLMProvider(Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    content: str
    model: str
    provider: LLMProvider
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    cached: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class LLMConfig:
    """Configuration for LLM calls."""
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    timeout_seconds: float = 60.0
    retry_attempts: int = 3


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._circuit_breaker = CircuitBreaker(
            self.provider_name,
            CircuitBreakerConfig(failure_threshold=3, timeout_seconds=60.0)
        )

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available."""
        pass

    @abstractmethod
    def _invoke(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """Internal invoke method to be implemented by subclasses."""
        pass

    def invoke(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """
        Invoke the LLM with circuit breaker protection.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt

        Returns:
            LLMResponse with the generated content
        """
        start_time = time.time()

        try:
            response = self._circuit_breaker.call(
                self._invoke,
                prompt,
                system_prompt
            )
            response.latency_ms = (time.time() - start_time) * 1000
            return response
        except Exception as e:
            logger.error(
                f"LLM invocation failed: {str(e)}",
                extra={"provider": self.provider_name, "error": str(e)}
            )
            raise


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider."""

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def is_available(self) -> bool:
        try:
            from langchain_ollama import OllamaLLM
            import requests
            response = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    @retry(max_attempts=3, initial_delay=1.0)
    def _invoke(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        from langchain_ollama import OllamaLLM

        llm = OllamaLLM(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=self.config.temperature,
        )

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        content = llm.invoke(full_prompt)

        return LLMResponse(
            content=content,
            model=settings.ollama_model,
            provider=LLMProvider.OLLAMA
        )


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider."""

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def is_available(self) -> bool:
        return settings.openai_api_key is not None

    @retry(max_attempts=3, initial_delay=1.0)
    def _invoke(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = llm.invoke(messages)

        return LLMResponse(
            content=response.content,
            model=settings.openai_model,
            provider=LLMProvider.OPENAI,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens")
        )


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def is_available(self) -> bool:
        return settings.anthropic_api_key is not None

    @retry(max_attempts=3, initial_delay=1.0)
    def _invoke(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = llm.invoke(messages)

        return LLMResponse(
            content=response.content,
            model=settings.anthropic_model,
            provider=LLMProvider.ANTHROPIC
        )


class LLMCache:
    """Simple in-memory LLM response cache."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # hash -> (response, timestamp)

    def _hash_key(self, prompt: str, system_prompt: Optional[str], model: str) -> str:
        """Generate cache key."""
        content = f"{model}:{system_prompt or ''}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, prompt: str, system_prompt: Optional[str], model: str) -> Optional[LLMResponse]:
        """Get cached response if available and not expired."""
        key = self._hash_key(prompt, system_prompt, model)
        if key in self._cache:
            response, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                response.cached = True
                return response
            else:
                del self._cache[key]
        return None

    def set(self, prompt: str, system_prompt: Optional[str], model: str, response: LLMResponse):
        """Cache a response."""
        if len(self._cache) >= self.max_size:
            # Remove oldest entries
            oldest = sorted(self._cache.items(), key=lambda x: x[1][1])[:self.max_size // 4]
            for key, _ in oldest:
                del self._cache[key]

        key = self._hash_key(prompt, system_prompt, model)
        self._cache[key] = (response, time.time())


class UnifiedLLM:
    """
    Unified LLM interface with automatic provider fallback and caching.

    Usage:
        llm = UnifiedLLM()
        response = llm.invoke("What is data governance?")

        # With system prompt
        response = llm.invoke(
            "Analyze this incident",
            system_prompt="You are a data quality expert."
        )
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        preferred_provider: Optional[LLMProvider] = None,
        enable_cache: bool = True
    ):
        self.config = config or LLMConfig()
        self.preferred_provider = preferred_provider
        self._cache = LLMCache() if enable_cache else None

        # Initialize providers in order of preference
        self._providers: List[BaseLLMProvider] = []
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers."""
        provider_classes = {
            LLMProvider.OLLAMA: OllamaProvider,
            LLMProvider.OPENAI: OpenAIProvider,
            LLMProvider.ANTHROPIC: AnthropicProvider
        }

        # Add preferred provider first
        if self.preferred_provider:
            provider_class = provider_classes.get(self.preferred_provider)
            if provider_class:
                provider = provider_class(self.config)
                if provider.is_available:
                    self._providers.append(provider)

        # Add other providers as fallbacks
        for provider_type, provider_class in provider_classes.items():
            if provider_type != self.preferred_provider:
                try:
                    provider = provider_class(self.config)
                    if provider.is_available:
                        self._providers.append(provider)
                except Exception as e:
                    logger.debug(f"Provider {provider_type} not available: {e}")

    @property
    def is_available(self) -> bool:
        """Check if any LLM provider is available."""
        return len(self._providers) > 0

    @property
    def available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return [p.provider_name for p in self._providers]

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_cache: bool = True
    ) -> LLMResponse:
        """
        Invoke LLM with automatic fallback.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            use_cache: Whether to use caching

        Returns:
            LLMResponse with generated content

        Raises:
            RuntimeError: If no LLM providers are available
        """
        if not self._providers:
            raise RuntimeError("No LLM providers available")

        # Check cache
        if use_cache and self._cache:
            cached = self._cache.get(
                prompt,
                system_prompt,
                self._providers[0].provider_name
            )
            if cached:
                logger.debug("Returning cached LLM response")
                return cached

        # Try providers in order
        last_error = None
        for provider in self._providers:
            try:
                response = provider.invoke(prompt, system_prompt)

                # Cache successful response
                if use_cache and self._cache:
                    self._cache.set(prompt, system_prompt, provider.provider_name, response)

                logger.info(
                    f"LLM invocation successful",
                    extra={
                        "provider": provider.provider_name,
                        "latency_ms": response.latency_ms,
                        "cached": response.cached
                    }
                )
                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"LLM provider {provider.provider_name} failed, trying next",
                    extra={"provider": provider.provider_name, "error": str(e)}
                )
                continue

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


def with_llm_fallback(
    fallback_func: Callable[..., T],
    llm: Optional[UnifiedLLM] = None
):
    """
    Decorator to provide fallback when LLM is unavailable.

    Usage:
        def template_based_answer(question):
            return f"Template answer for: {question}"

        @with_llm_fallback(template_based_answer)
        def llm_answer(question):
            llm = UnifiedLLM()
            return llm.invoke(question).content
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            _llm = llm or UnifiedLLM()

            if not _llm.is_available:
                logger.warning(
                    "No LLM available, using fallback",
                    extra={"function": func.__name__}
                )
                return fallback_func(*args, **kwargs)

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"LLM call failed, using fallback: {e}",
                    extra={"function": func.__name__, "error": str(e)}
                )
                return fallback_func(*args, **kwargs)

        return wrapper
    return decorator


# Global LLM instance (lazy initialization)
_global_llm: Optional[UnifiedLLM] = None


def get_llm() -> UnifiedLLM:
    """Get the global LLM instance."""
    global _global_llm
    if _global_llm is None:
        _global_llm = UnifiedLLM()
    return _global_llm


def get_llm_if_available() -> Optional[UnifiedLLM]:
    """Get LLM if available, None otherwise."""
    llm = get_llm()
    return llm if llm.is_available else None
