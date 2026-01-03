"""
Semantic Search for Data Products using real embeddings.
Uses Ollama for generating embeddings when available, with fallback to simple TF-IDF.
"""
from src.graph.manager import Neo4jManager
import numpy as np
import os
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Provides embeddings using Ollama or fallback methods."""

    def __init__(self):
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self._ollama_available = None

    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            import requests
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            self._ollama_available = response.status_code == 200
        except Exception:
            self._ollama_available = False

        return self._ollama_available

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using Ollama or fallback."""
        if self._check_ollama():
            return self._ollama_embedding(text)
        return self._fallback_embedding(text)

    def _ollama_embedding(self, text: str) -> List[float]:
        """Get embedding from Ollama."""
        try:
            import requests
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("embedding", [])
        except Exception as e:
            logger.warning(f"Ollama embedding failed: {e}")

        return self._fallback_embedding(text)

    def _fallback_embedding(self, text: str, dim: int = 384) -> List[float]:
        """
        Simple hash-based embedding fallback.
        Creates a deterministic embedding based on text content.
        """
        import hashlib

        # Normalize text
        text = text.lower().strip()
        words = text.split()

        # Create embedding vector
        embedding = np.zeros(dim)

        for i, word in enumerate(words):
            # Hash each word to get a position and value
            word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
            positions = [(word_hash >> (j * 8)) % dim for j in range(4)]
            values = [((word_hash >> (j * 4)) % 100) / 100.0 - 0.5 for j in range(4)]

            for pos, val in zip(positions, values):
                embedding[pos] += val * (1.0 / (i + 1))  # Decay by position

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding.tolist()


class SemanticMarketplace:
    """Semantic search marketplace for data products."""

    def __init__(self):
        self.embedding_provider = EmbeddingProvider()
        self._manager: Optional[Neo4jManager] = None

    @property
    def manager(self) -> Neo4jManager:
        if self._manager is None:
            self._manager = Neo4jManager()
        return self._manager

    def close(self):
        """Close the Neo4j connection."""
        if self._manager:
            self._manager.close()
            self._manager = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        return self.embedding_provider.get_embedding(text)

    def index_product(self, product_id: str) -> bool:
        """Index a product by generating and storing its embedding."""
        q = """
        MATCH (p:DataProduct {id: $id})
        RETURN p.name as name, p.description as description, p.type as type
        """
        res = self.manager.execute_query(q, {"id": product_id})

        if not res:
            return False

        record = res[0]
        # Combine name, description, and type for richer embedding
        text = f"{record.get('name', '')} {record.get('description', '')} {record.get('type', '')}"
        embedding = self.generate_embedding(text)

        # Store embedding
        self.manager.execute_query(
            "MATCH (p:DataProduct {id: $id}) SET p.embedding = $emb",
            {"id": product_id, "emb": embedding}
        )
        return True

    def index_all_products(self) -> int:
        """Index all products that don't have embeddings."""
        q = "MATCH (p:DataProduct) WHERE p.embedding IS NULL RETURN p.id as id"
        res = self.manager.execute_query(q, {})

        count = 0
        for record in res:
            if self.index_product(record["id"]):
                count += 1

        logger.info(f"Indexed {count} products")
        return count

    def search(self, query_text: str, limit: int = 10) -> List[dict]:
        """
        Search for products using semantic similarity.

        Args:
            query_text: The search query
            limit: Maximum number of results to return

        Returns:
            List of products with similarity scores
        """
        query_emb = np.array(self.generate_embedding(query_text))

        # Fetch all products with embeddings
        res = self.manager.execute_query(
            """
            MATCH (p:DataProduct)
            WHERE p.embedding IS NOT NULL
            RETURN p.id as id, p.name as name, p.description as description,
                   p.type as type, p.status as status, p.embedding as embedding
            """,
            {}
        )

        results = []
        for r in res:
            db_emb = np.array(r['embedding'])

            # Cosine similarity
            dot_product = np.dot(query_emb, db_emb)
            norm_query = np.linalg.norm(query_emb)
            norm_db = np.linalg.norm(db_emb)

            if norm_query > 0 and norm_db > 0:
                score = float(dot_product / (norm_query * norm_db))
            else:
                score = 0.0

            results.append({
                "id": r['id'],
                "name": r['name'],
                "description": r.get('description'),
                "type": r.get('type'),
                "status": r.get('status'),
                "score": score
            })

        # Sort by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]

    def hybrid_search(self, query_text: str, limit: int = 10) -> List[dict]:
        """
        Hybrid search combining semantic and keyword search.
        Falls back to keyword search if no embeddings available.
        """
        # First try semantic search
        semantic_results = self.search(query_text, limit * 2)

        if semantic_results:
            return semantic_results[:limit]

        # Fallback to keyword search
        return self.keyword_search(query_text, limit)

    def keyword_search(self, query_text: str, limit: int = 10) -> List[dict]:
        """Fallback keyword-based search."""
        q = """
        MATCH (p:DataProduct)
        WHERE toLower(p.name) CONTAINS toLower($query)
           OR toLower(p.description) CONTAINS toLower($query)
        RETURN p.id as id, p.name as name, p.description as description,
               p.type as type, p.status as status
        LIMIT $limit
        """
        res = self.manager.execute_query(q, {"query": query_text, "limit": limit})

        return [
            {
                "id": r['id'],
                "name": r['name'],
                "description": r.get('description'),
                "type": r.get('type'),
                "status": r.get('status'),
                "score": 1.0  # Keyword match has max score
            }
            for r in res
        ]


# Module-level functions for convenience
def semantic_search(query: str, limit: int = 10) -> list:
    """Perform semantic search for data products."""
    with SemanticMarketplace() as marketplace:
        return marketplace.hybrid_search(query, limit)


def index_product(product_id: str) -> bool:
    """Index a single product."""
    with SemanticMarketplace() as marketplace:
        return marketplace.index_product(product_id)


def index_all_products() -> int:
    """Index all products without embeddings."""
    with SemanticMarketplace() as marketplace:
        return marketplace.index_all_products()
