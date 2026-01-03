"""
Intent Classifier for Hybrid RAG
Determines whether a question should be answered via:
- Semantic search (embedding similarity)
- Graph query (Cypher generation)
- Keyword search (exact matching)
- Hybrid (combination)

Supports LLM fallback for ambiguous or complex queries.
"""
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import re
import json
import logging

logger = logging.getLogger(__name__)

# Try to import LLM components
try:
    from src.core.llm import UnifiedLLM, LLMConfig
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False


class QueryIntent(Enum):
    """Types of query intents."""
    SEMANTIC = "semantic"       # Conceptual questions, recommendations
    GRAPH = "graph"             # Structural queries, counts, relationships
    KEYWORD = "keyword"         # Exact name/ID lookups
    HYBRID = "hybrid"           # Needs multiple approaches


@dataclass
class ClassificationResult:
    """Result of intent classification."""
    primary_intent: QueryIntent
    secondary_intent: QueryIntent | None
    confidence: float
    reasoning: str
    extracted_entities: List[str]
    suggested_approach: str


class IntentClassifier:
    """
    Classifies questions to determine the best retrieval approach.
    Uses rule-based classification with LLM fallback for ambiguous queries.
    """

    def __init__(self, use_llm_fallback: bool = True):
        """
        Initialize the intent classifier.

        Args:
            use_llm_fallback: Whether to use LLM for ambiguous classifications
        """
        self.use_llm_fallback = use_llm_fallback and LLM_AVAILABLE
        self._llm = None

        if self.use_llm_fallback:
            try:
                config = LLMConfig()
                self._llm = UnifiedLLM(config)
                logger.info("LLM fallback enabled for intent classification")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM for classification: {e}")
                self.use_llm_fallback = False

    # Keywords that suggest graph/structural queries
    GRAPH_KEYWORDS = [
        "how many", "count", "number of", "total",
        "list", "show all", "find all",
        "depends on", "consumes", "downstream", "upstream", "lineage",
        "affected", "impact", "connected",
        "created", "updated", "when",
        "who owns", "owner of",
        "contract", "rule", "sla", "policy",
        "incident", "violation", "breach"
    ]

    # Keywords that suggest semantic/conceptual queries
    SEMANTIC_KEYWORDS = [
        "what is", "explain", "describe", "tell me about",
        "similar to", "like", "related",
        "best practice", "recommend", "suggest",
        "why", "how does", "how can",
        "compare", "difference between"
    ]

    # Keywords that suggest exact lookup
    KEYWORD_PATTERNS = [
        r"DP\d+",           # Product IDs
        r"INC_\w+",         # Incident IDs
        r"CON_\w+",         # Contract IDs
        r'"[^"]+"',         # Quoted strings
        r"'[^']+'",         # Single quoted
    ]

    def classify(self, question: str) -> ClassificationResult:
        """
        Classify a question to determine retrieval approach.

        Args:
            question: Natural language question

        Returns:
            ClassificationResult with intent and metadata
        """
        question_lower = question.lower()

        # Extract entities
        entities = self._extract_entities(question)

        # Score each intent
        graph_score = self._score_graph_intent(question_lower)
        semantic_score = self._score_semantic_intent(question_lower)
        keyword_score = self._score_keyword_intent(question, entities)

        # Determine primary intent
        scores = {
            QueryIntent.GRAPH: graph_score,
            QueryIntent.SEMANTIC: semantic_score,
            QueryIntent.KEYWORD: keyword_score
        }

        sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_intents[0]
        secondary = sorted_intents[1] if sorted_intents[1][1] > 0.3 else None

        # Check if hybrid is better
        if primary[1] < 0.7 and secondary and secondary[1] > 0.4:
            final_intent = QueryIntent.HYBRID
            confidence = (primary[1] + secondary[1]) / 2
            approach = f"Combine {primary[0].value} and {secondary[0].value} approaches"
        else:
            final_intent = primary[0]
            confidence = primary[1]
            approach = self._get_approach_description(final_intent)

        reasoning = self._build_reasoning(question_lower, scores, entities)

        # Use LLM fallback for low-confidence or ambiguous classifications
        if confidence < 0.5 and self.use_llm_fallback and self._llm:
            llm_result = self._classify_with_llm(question)
            if llm_result and llm_result.confidence > confidence:
                return llm_result

        return ClassificationResult(
            primary_intent=final_intent,
            secondary_intent=secondary[0] if secondary else None,
            confidence=confidence,
            reasoning=reasoning,
            extracted_entities=entities,
            suggested_approach=approach
        )

    def _classify_with_llm(self, question: str) -> Optional[ClassificationResult]:
        """
        Use LLM to classify ambiguous or complex queries.
        Called as fallback when rule-based confidence is low.
        """
        if not self._llm:
            return None

        prompt = f"""Classify the following question to determine the best retrieval approach for a data product management system.

QUESTION: {question}

Available approaches:
1. SEMANTIC - For conceptual questions, explanations, recommendations, comparisons
2. GRAPH - For structural queries: counts, relationships, lineage, dependencies, lists
3. KEYWORD - For exact lookups by ID or name
4. HYBRID - When multiple approaches are needed

Analyze the question and return a JSON object:
{{
    "intent": "SEMANTIC|GRAPH|KEYWORD|HYBRID",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation",
    "entities": ["any extracted entity names or IDs"],
    "approach": "description of how to answer this question"
}}
"""

        try:
            response = self._llm.invoke(
                prompt,
                system_prompt="You are a query classification expert. Analyze questions and determine the best retrieval approach. Return valid JSON only."
            )

            if response.success and response.content:
                return self._parse_llm_classification(response.content)

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}")

        return None

    def _parse_llm_classification(self, content: str) -> Optional[ClassificationResult]:
        """Parse LLM classification response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            intent_str = data.get("intent", "HYBRID").upper()
            intent_map = {
                "SEMANTIC": QueryIntent.SEMANTIC,
                "GRAPH": QueryIntent.GRAPH,
                "KEYWORD": QueryIntent.KEYWORD,
                "HYBRID": QueryIntent.HYBRID
            }

            return ClassificationResult(
                primary_intent=intent_map.get(intent_str, QueryIntent.HYBRID),
                secondary_intent=None,
                confidence=float(data.get("confidence", 0.7)),
                reasoning=f"[LLM] {data.get('reasoning', 'LLM-based classification')}",
                extracted_entities=data.get("entities", []),
                suggested_approach=data.get("approach", "Use LLM-recommended approach")
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM classification: {e}")
            return None

    def _score_graph_intent(self, question: str) -> float:
        """Score how likely the question needs graph queries."""
        score = 0.0

        for keyword in self.GRAPH_KEYWORDS:
            if keyword in question:
                score += 0.2

        # Structural question patterns
        if re.search(r"(how many|count|number)", question):
            score += 0.3
        if re.search(r"(depends|consumes|upstream|downstream|lineage)", question):
            score += 0.4
        if re.search(r"(incident|violation|contract|rule)", question):
            score += 0.2
        if re.search(r"(list|show|find) (all|the)", question):
            score += 0.2

        return min(score, 1.0)

    def _score_semantic_intent(self, question: str) -> float:
        """Score how likely the question needs semantic search."""
        score = 0.3  # Base score for all questions

        for keyword in self.SEMANTIC_KEYWORDS:
            if keyword in question:
                score += 0.15

        # Conceptual patterns
        if re.search(r"(what is|explain|describe)", question):
            score += 0.3
        if re.search(r"(similar|like|related)", question):
            score += 0.3
        if re.search(r"(recommend|suggest|best)", question):
            score += 0.2
        if re.search(r"(why|how does|how can)", question):
            score += 0.2

        return min(score, 1.0)

    def _score_keyword_intent(self, question: str, entities: List[str]) -> float:
        """Score how likely the question needs exact keyword lookup."""
        score = 0.0

        # Direct ID lookups get high keyword score
        if entities:
            score += 0.3 * len(entities)

        # Quoted strings suggest exact match
        if '"' in question or "'" in question:
            score += 0.3

        # Specific lookups
        if re.search(r"(get|fetch|retrieve|lookup)\s", question.lower()):
            score += 0.2

        return min(score, 1.0)

    def _extract_entities(self, question: str) -> List[str]:
        """Extract entity identifiers from the question."""
        entities = []

        for pattern in self.KEYWORD_PATTERNS:
            matches = re.findall(pattern, question)
            entities.extend(matches)

        # Remove quotes from quoted strings
        entities = [e.strip("'\"") for e in entities]

        return list(set(entities))

    def _get_approach_description(self, intent: QueryIntent) -> str:
        """Get a description of the approach for this intent."""
        descriptions = {
            QueryIntent.GRAPH: "Use Cypher query generation to traverse the knowledge graph",
            QueryIntent.SEMANTIC: "Use embedding similarity search for conceptual matching",
            QueryIntent.KEYWORD: "Use exact keyword matching for ID/name lookups",
            QueryIntent.HYBRID: "Combine multiple retrieval methods for best results"
        }
        return descriptions.get(intent, "Unknown approach")

    def _build_reasoning(
        self,
        question: str,
        scores: dict,
        entities: List[str]
    ) -> str:
        """Build a reasoning explanation for the classification."""
        parts = []

        if entities:
            parts.append(f"Found specific entities: {', '.join(entities)}")

        highest = max(scores.items(), key=lambda x: x[1])
        parts.append(f"Highest scoring intent: {highest[0].value} ({highest[1]:.2f})")

        # Explain why
        if scores[QueryIntent.GRAPH] > 0.5:
            parts.append("Question involves counting, relationships, or structural data")
        if scores[QueryIntent.SEMANTIC] > 0.5:
            parts.append("Question is conceptual or asks for explanations")
        if scores[QueryIntent.KEYWORD] > 0.5:
            parts.append("Question references specific IDs or names")

        return "; ".join(parts)
