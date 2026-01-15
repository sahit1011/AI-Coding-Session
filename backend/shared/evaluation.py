"""
Evaluation Framework for RAG Pipeline Quality.

Metrics:
- Precision@K: Fraction of top K results that are relevant
- Recall@K: Fraction of relevant results found in top K
- MRR: Mean Reciprocal Rank
- NDCG: Normalized Discounted Cumulative Gain
- Query Latency: Response time
"""

from typing import List, Dict, Any, Optional
import time
import numpy as np


class RAGEvaluator:
    """Evaluate RAG pipeline performance."""
    
    def __init__(self):
        self.query_history: List[Dict[str, Any]] = []
        self.ground_truth: Dict[str, List[str]] = {}  # query -> list of relevant chunk IDs
    
    def add_ground_truth(self, query: str, relevant_chunk_ids: List[str]):
        """Add ground truth labels for a query."""
        self.ground_truth[query] = relevant_chunk_ids
    
    def evaluate_search(
        self,
        query: str,
        results: List[Dict[str, Any]],
        k: int = 10
    ) -> Dict[str, float]:
        """
        Evaluate search results against ground truth.
        
        Returns:
            Dictionary with precision@k, recall@k, MRR, NDCG
        """
        if query not in self.ground_truth:
            return {
                "precision_at_k": None,
                "recall_at_k": None,
                "mrr": None,
                "ndcg": None
            }
        
        relevant_ids = set(self.ground_truth[query])
        result_ids = [r["id"] for r in results[:k]]
        
        # Precision@K: Fraction of top K that are relevant
        relevant_in_top_k = sum(1 for rid in result_ids if rid in relevant_ids)
        precision_at_k = relevant_in_top_k / k if k > 0 else 0
        
        # Recall@K: Fraction of relevant found in top K
        recall_at_k = relevant_in_top_k / len(relevant_ids) if len(relevant_ids) > 0 else 0
        
        # MRR: Mean Reciprocal Rank (1/rank of first relevant)
        mrr = 0
        for rank, rid in enumerate(result_ids, 1):
            if rid in relevant_ids:
                mrr = 1.0 / rank
                break
        
        # NDCG: Normalized Discounted Cumulative Gain
        dcg = 0
        for rank, rid in enumerate(result_ids, 1):
            if rid in relevant_ids:
                dcg += 1.0 / np.log2(rank + 1)
        
        # Ideal DCG (all relevant at top)
        ideal_dcg = sum(1.0 / np.log2(i + 2) for i in range(min(len(relevant_ids), k)))
        ndcg = dcg / ideal_dcg if ideal_dcg > 0 else 0
        
        return {
            "precision_at_k": precision_at_k,
            "recall_at_k": recall_at_k,
            "mrr": mrr,
            "ndcg": ndcg,
            "relevant_found": relevant_in_top_k,
            "total_relevant": len(relevant_ids)
        }
    
    def log_query(
        self,
        query: str,
        results: List[Dict[str, Any]],
        query_time_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a query for analytics."""
        self.query_history.append({
            "query": query,
            "result_count": len(results),
            "query_time_ms": query_time_ms,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get query analytics."""
        if not self.query_history:
            return {}
        
        query_times = [q["query_time_ms"] for q in self.query_history]
        
        return {
            "total_queries": len(self.query_history),
            "avg_query_time_ms": np.mean(query_times),
            "p50_query_time_ms": np.percentile(query_times, 50),
            "p95_query_time_ms": np.percentile(query_times, 95),
            "p99_query_time_ms": np.percentile(query_times, 99),
            "avg_results_per_query": np.mean([q["result_count"] for q in self.query_history])
        }
    
    def compare_strategies(
        self,
        query: str,
        strategy_a_results: List[Dict[str, Any]],
        strategy_b_results: List[Dict[str, Any]],
        strategy_a_name: str = "Strategy A",
        strategy_b_name: str = "Strategy B",
        k: int = 10
    ) -> Dict[str, Any]:
        """Compare two search strategies."""
        eval_a = self.evaluate_search(query, strategy_a_results, k)
        eval_b = self.evaluate_search(query, strategy_b_results, k)
        
        return {
            strategy_a_name: eval_a,
            strategy_b_name: eval_b,
            "improvement": {
                "precision": eval_b["precision_at_k"] - eval_a["precision_at_k"] if eval_a["precision_at_k"] else None,
                "recall": eval_b["recall_at_k"] - eval_a["recall_at_k"] if eval_a["recall_at_k"] else None,
                "mrr": eval_b["mrr"] - eval_a["mrr"] if eval_a["mrr"] else None,
                "ndcg": eval_b["ndcg"] - eval_a["ndcg"] if eval_a["ndcg"] else None
            }
        }


# Sample ground truth for testing
SAMPLE_GROUND_TRUTH = {
    "how to handle large file uploads": [
        "chunk_0033",  # S3 multipart upload
        "chunk_0038",  # Memory management
    ],
    "video encoding optimization": [
        "chunk_0000",  # Video encoding
        "chunk_0011",  # Quality strategy
    ],
    "WebRTC signaling": [
        "chunk_0022",  # WebRTC implementation
    ]
}


def create_test_ground_truth(chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Create ground truth labels based on chunk content.
    
    This is a simple heuristic - in production, use human labeling.
    """
    ground_truth = {}
    
    # Map queries to likely relevant chunks based on keywords
    query_keywords = {
        "how to handle large file uploads": ["upload", "multipart", "S3", "large", "file"],
        "video encoding optimization": ["encoding", "video", "optimize", "performance"],
        "WebRTC signaling": ["WebRTC", "signaling", "peer"],
        "memory optimization": ["memory", "RAM", "buffer", "optimize"],
        "error handling": ["error", "exception", "handle", "retry"],
    }
    
    for query, keywords in query_keywords.items():
        relevant = []
        for chunk in chunks:
            content_lower = chunk["content"].lower()
            if any(kw.lower() in content_lower for kw in keywords):
                relevant.append(chunk["id"])
        ground_truth[query] = relevant[:5]  # Top 5 most relevant
    
    return ground_truth

