"""
Result Fusion for Hybrid RAG
Combines results from multiple retrieval sources (semantic, graph, keyword).
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class RankedResult:
    """A result with its fusion score."""
    content: Dict[str, Any]
    source: str
    original_score: float
    fusion_score: float
    rank: int


@dataclass
class FusionResult:
    """Result of fusion operation."""
    results: List[RankedResult]
    sources_used: List[str]
    total_candidates: int


class ResultFusion:
    """
    Fuses results from multiple retrieval sources using reciprocal rank fusion.
    """

    def __init__(self, k: int = 60):
        """
        Initialize the fusion engine.

        Args:
            k: Reciprocal rank fusion parameter (default 60)
        """
        self.k = k

    def fuse(
        self,
        semantic_results: List[Dict[str, Any]] = None,
        graph_results: List[Dict[str, Any]] = None,
        keyword_results: List[Dict[str, Any]] = None,
        weights: Dict[str, float] = None
    ) -> FusionResult:
        """
        Fuse results from multiple sources using weighted reciprocal rank fusion.

        Args:
            semantic_results: Results from semantic/embedding search
            graph_results: Results from Cypher/graph queries
            keyword_results: Results from keyword matching
            weights: Optional weights for each source

        Returns:
            FusionResult with ranked combined results
        """
        if weights is None:
            weights = {
                "semantic": 1.0,
                "graph": 1.2,  # Slightly favor structured queries
                "keyword": 1.1
            }

        # Collect all results with their sources
        all_results = []

        if semantic_results:
            for i, result in enumerate(semantic_results):
                all_results.append({
                    "content": result,
                    "source": "semantic",
                    "rank": i + 1,
                    "weight": weights.get("semantic", 1.0)
                })

        if graph_results:
            for i, result in enumerate(graph_results):
                all_results.append({
                    "content": result,
                    "source": "graph",
                    "rank": i + 1,
                    "weight": weights.get("graph", 1.0)
                })

        if keyword_results:
            for i, result in enumerate(keyword_results):
                all_results.append({
                    "content": result,
                    "source": "keyword",
                    "rank": i + 1,
                    "weight": weights.get("keyword", 1.0)
                })

        # Calculate fusion scores
        fusion_scores = defaultdict(float)
        result_map = {}

        for item in all_results:
            # Create a key for deduplication
            content_key = self._get_content_key(item["content"])

            # Reciprocal rank fusion with weight
            rrf_score = item["weight"] / (self.k + item["rank"])
            fusion_scores[content_key] += rrf_score

            # Keep the highest-scored version of duplicate content
            if content_key not in result_map or rrf_score > result_map[content_key]["score"]:
                result_map[content_key] = {
                    "content": item["content"],
                    "source": item["source"],
                    "score": rrf_score
                }

        # Sort by fusion score
        sorted_keys = sorted(fusion_scores.keys(), key=lambda k: fusion_scores[k], reverse=True)

        # Build ranked results
        ranked_results = []
        sources_used = set()

        for rank, key in enumerate(sorted_keys, 1):
            item = result_map[key]
            sources_used.add(item["source"])

            ranked_results.append(RankedResult(
                content=item["content"],
                source=item["source"],
                original_score=item["score"],
                fusion_score=fusion_scores[key],
                rank=rank
            ))

        return FusionResult(
            results=ranked_results,
            sources_used=list(sources_used),
            total_candidates=len(all_results)
        )

    def _get_content_key(self, content: Dict[str, Any]) -> str:
        """Generate a deduplication key for content."""
        # Use ID if available
        if "id" in content:
            return str(content["id"])

        # Use name + type if available
        if "name" in content:
            type_str = content.get("type", content.get("node_type", ""))
            return f"{content['name']}:{type_str}"

        # Fall back to string representation
        return str(sorted(content.items()))

    def rerank_by_relevance(
        self,
        results: List[RankedResult],
        question: str,
        top_k: int = 10
    ) -> List[RankedResult]:
        """
        Re-rank results based on relevance to the question.
        Simple keyword-based reranking.

        Args:
            results: Fused results to rerank
            question: Original question
            top_k: Number of results to return

        Returns:
            Reranked list of results
        """
        question_words = set(question.lower().split())

        def relevance_score(result: RankedResult) -> float:
            """Calculate relevance based on keyword overlap."""
            content = result.content
            content_str = " ".join(str(v).lower() for v in content.values())
            content_words = set(content_str.split())

            overlap = len(question_words & content_words)
            base_score = result.fusion_score

            # Boost by relevance
            return base_score * (1 + overlap * 0.1)

        # Sort by combined score
        sorted_results = sorted(results, key=relevance_score, reverse=True)

        # Update ranks
        for i, result in enumerate(sorted_results[:top_k], 1):
            result.rank = i

        return sorted_results[:top_k]
