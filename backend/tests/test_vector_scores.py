"""
Test and Compare Vector Search Scores in Basic vs Enhanced Mode.

Explains:
1. What the negative scores mean
2. How ChromaDB distance relates to similarity
3. Comparison between basic and enhanced modes
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_loader import load_session_files
from enhanced.enhanced_chunking import create_overlapping_chunks
from basic.search_engine import SearchEngine
from enhanced.enhanced_search import EnhancedSearchEngine
from shared.config import ENHANCED_SEARCH_CONFIG


def explain_scores():
    """Explain what the scores mean."""
    print("=" * 80)
    print("UNDERSTANDING VECTOR SEARCH SCORES")
    print("=" * 80)
    print("""
ChromaDB uses COSINE DISTANCE (not similarity):
- Distance = 0.0  → Perfect match (identical vectors)
- Distance = 1.0  → Orthogonal (unrelated)
- Distance = 2.0  → Opposite (completely different)

We convert to SIMILARITY: similarity = 1 - distance
- Similarity = 1.0  → Perfect match (distance = 0)
- Similarity = 0.0  → Unrelated (distance = 1)
- Similarity = -1.0 → Opposite (distance = 2)

NEGATIVE SCORES mean:
- Distance > 1.0 (vectors are more than orthogonal)
- The query and chunk are somewhat dissimilar
- BUT: They might still be relevant if other methods (BM25, Graph) boost them

POSITIVE SCORES mean:
- Distance < 1.0 (vectors are somewhat similar)
- Higher positive = more similar
""")


def test_basic_mode(query: str):
    """Test query in basic mode."""
    from shared.data_loader import create_searchable_chunks
    
    print("\n" + "=" * 80)
    print("BASIC MODE - Vector Search Only")
    print("=" * 80)
    
    # Load data
    data_dir = "../data" if os.path.exists("../data") else "data"
    sessions_data = load_session_files(data_dir)
    chunks = create_searchable_chunks(sessions_data)
    
    # Initialize basic search
    engine = SearchEngine(model_name="all-MiniLM-L6-v2")
    engine.index_chunks(chunks, force_reindex=False)
    
    # Search
    print(f"\nQuery: '{query}'")
    print(f"Model: all-MiniLM-L6-v2 (384-dim, fast)")
    print(f"Method: Pure vector search (no BM25, no graph, no reranking)")
    
    results = engine.search(query, limit=5)
    
    print(f"\nResults ({len(results['results'])}):")
    for i, result in enumerate(results['results'][:5], 1):
        chunk_id = result['id']
        score = result['score']
        engineer = result['engineer']['name']
        project = result['project']['name']
        content_preview = result['content'][:100].replace("\n", " ")
        
        # Explain score
        distance = 1 - score
        if score > 0.5:
            interpretation = "Very similar"
        elif score > 0:
            interpretation = "Somewhat similar"
        elif score > -0.5:
            interpretation = "Somewhat dissimilar"
        else:
            interpretation = "Very dissimilar"
        
        print(f"\n  {i}. {chunk_id}")
        print(f"     Score: {score:.4f} (distance: {distance:.4f})")
        print(f"     Interpretation: {interpretation}")
        print(f"     {engineer} / {project}")
        print(f"     {content_preview}...")
    
    print(f"\n  Query time: {results['query_time_ms']:.2f}ms")
    return results


def test_enhanced_mode(query: str):
    """Test query in enhanced mode."""
    print("\n" + "=" * 80)
    print("ENHANCED MODE - Hybrid Search (Vector + BM25 + Graph + Reranking)")
    print("=" * 80)
    
    # Load data
    data_dir = "../data" if os.path.exists("../data") else "data"
    sessions_data = load_session_files(data_dir)
    chunks = create_overlapping_chunks(sessions_data, window_size=2, overlap=1)
    
    # Initialize enhanced search
    engine = EnhancedSearchEngine(
        embedding_model=ENHANCED_SEARCH_CONFIG["embedding_model"],
        reranker_model=ENHANCED_SEARCH_CONFIG["reranker_model"],
        use_reranking=ENHANCED_SEARCH_CONFIG["use_reranking"],
        hybrid_weight=ENHANCED_SEARCH_CONFIG["hybrid_weight"],
        groq_api_key=ENHANCED_SEARCH_CONFIG.get("groq_api_key"),
        use_groq_expansion=ENHANCED_SEARCH_CONFIG.get("expand_query", False)
    )
    engine.index_chunks(chunks, force_reindex=False)
    
    # Get vector search results directly
    expanded_query = engine._expand_query(query) if ENHANCED_SEARCH_CONFIG.get("expand_query") else query
    vector_results = engine._vector_search(expanded_query, k=5)
    
    print(f"\nQuery: '{query}'")
    if expanded_query != query:
        print(f"Expanded: '{expanded_query}'")
    print(f"Model: {ENHANCED_SEARCH_CONFIG['embedding_model']} (768-dim, better quality)")
    print(f"Method: Vector (70%) + BM25 (30%) + Graph (20% boost) + Reranking")
    
    print(f"\nVector Search Results (before combination):")
    for i, (idx, score) in enumerate(vector_results[:5], 1):
        chunk_id = engine.chunk_ids[idx]
        engineer = engine.metadatas[idx].get("engineer_name", "")
        project = engine.metadatas[idx].get("project_name", "")
        content_preview = engine.documents[idx][:100].replace("\n", " ")
        
        # Explain score
        distance = 1 - score
        if score > 0.5:
            interpretation = "Very similar"
        elif score > 0:
            interpretation = "Somewhat similar"
        elif score > -0.5:
            interpretation = "Somewhat dissimilar"
        else:
            interpretation = "Very dissimilar"
        
        print(f"\n  {i}. {chunk_id}")
        print(f"     Vector Score: {score:.4f} (distance: {distance:.4f})")
        print(f"     Interpretation: {interpretation}")
        print(f"     {engineer} / {project}")
        print(f"     {content_preview}...")
    
    # Full search
    print(f"\n" + "-" * 80)
    print("FULL ENHANCED SEARCH (with all methods):")
    print("-" * 80)
    results = engine.search(query, limit=5, expand_query=ENHANCED_SEARCH_CONFIG.get("expand_query", False))
    
    print(f"\nFinal Results ({len(results['results'])}):")
    for i, result in enumerate(results['results'][:5], 1):
        chunk_id = result['id']
        score = result.get('score', 0)
        rerank_score = result.get('rerank_score', None)
        engineer = result['engineer']['name']
        project = result['project']['name']
        content_preview = result['content'][:100].replace("\n", " ")
        
        print(f"\n  {i}. {chunk_id}")
        print(f"     Final Score: {score:.4f}")
        if rerank_score is not None:
            print(f"     Rerank Score: {rerank_score:.4f}")
        print(f"     {engineer} / {project}")
        print(f"     {content_preview}...")
    
    print(f"\n  Query time: {results['query_time_ms']:.2f}ms")
    print(f"  Query expanded: {results.get('query_expanded', 'No')}")
    print(f"  Reranked: {results.get('reranked', False)}")
    
    return results


def compare_modes(query: str):
    """Compare basic vs enhanced mode side by side."""
    print("\n" + "=" * 80)
    print("COMPARISON: BASIC vs ENHANCED MODE")
    print("=" * 80)
    
    # Basic mode
    print("\n📊 BASIC MODE:")
    basic_results = test_basic_mode(query)
    
    # Enhanced mode
    print("\n📊 ENHANCED MODE:")
    enhanced_results = test_enhanced_mode(query)
    
    # Comparison
    print("\n" + "=" * 80)
    print("KEY DIFFERENCES")
    print("=" * 80)
    print(f"""
1. MODEL:
   Basic:  all-MiniLM-L6-v2 (384-dim, faster, ~90% quality)
   Enhanced: all-mpnet-base-v2 (768-dim, slower, better quality)

2. SEARCH METHODS:
   Basic:  Vector only
   Enhanced: Vector + BM25 + Knowledge Graph

3. POST-PROCESSING:
   Basic:  None
   Enhanced: Cross-encoder reranking

4. SPEED:
   Basic:  {basic_results['query_time_ms']:.2f}ms
   Enhanced: {enhanced_results['query_time_ms']:.2f}ms

5. RESULTS:
   Basic:  Top result score: {basic_results['results'][0]['score']:.4f}
   Enhanced: Top result score: {enhanced_results['results'][0].get('score', 0):.4f}
   
6. WHY NEGATIVE SCORES?
   - ChromaDB returns COSINE DISTANCE (0-2 range)
   - We convert: similarity = 1 - distance
   - Negative = distance > 1.0 (somewhat dissimilar)
   - BUT: Enhanced mode combines with BM25/Graph to boost relevant results
   - Reranking reorders based on actual relevance, not just vector similarity
""")


if __name__ == "__main__":
    import sys
    
    query = "video encoding optimization"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    
    explain_scores()
    compare_modes(query)

