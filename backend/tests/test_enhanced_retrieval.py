"""
Test Enhanced Retrieval Pipeline - Step by Step.

Shows:
1. Vector search results
2. BM25 search results
3. Knowledge Graph search results
4. Combined scores
5. Reranking
6. Final results
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_loader import load_session_files
from enhanced.enhanced_chunking import create_overlapping_chunks
from enhanced.enhanced_search import EnhancedSearchEngine
from shared.config import ENHANCED_SEARCH_CONFIG


def test_query(query: str, limit: int = 5):
    """Test a query and show step-by-step retrieval."""
    print("=" * 80)
    print(f"TESTING QUERY: '{query}'")
    print("=" * 80)
    
    # Load data and create chunks
    data_dir = "../data" if os.path.exists("../data") else "data"
    sessions_data = load_session_files(data_dir)
    chunks = create_overlapping_chunks(sessions_data, window_size=2, overlap=1)
    
    # Initialize enhanced search engine
    print("\n[1/6] Initializing Enhanced Search Engine...")
    engine = EnhancedSearchEngine(
        embedding_model=ENHANCED_SEARCH_CONFIG["embedding_model"],
        reranker_model=ENHANCED_SEARCH_CONFIG["reranker_model"],
        use_reranking=ENHANCED_SEARCH_CONFIG["use_reranking"],
        hybrid_weight=ENHANCED_SEARCH_CONFIG["hybrid_weight"],
        groq_api_key=ENHANCED_SEARCH_CONFIG.get("groq_api_key"),
        use_groq_expansion=ENHANCED_SEARCH_CONFIG.get("expand_query", False)
    )
    
    # Index chunks
    print("\n[2/6] Indexing chunks...")
    engine.index_chunks(chunks, force_reindex=False)
    
    # Query expansion
    print("\n[3/6] Query Processing...")
    expanded_query = engine._expand_query(query) if ENHANCED_SEARCH_CONFIG.get("expand_query") else query
    if expanded_query != query:
        print(f"  Original: '{query}'")
        print(f"  Expanded: '{expanded_query}'")
    else:
        print(f"  Query: '{query}' (no expansion)")
    
    # Step 1: Vector Search
    print("\n" + "=" * 80)
    print("[4/6] STEP 1: VECTOR SEARCH (Semantic Similarity)")
    print("=" * 80)
    vector_results = engine._vector_search(expanded_query, k=20)
    print(f"  Retrieved: {len(vector_results)} candidates")
    print(f"\n  Top 5 Vector Results:")
    for i, (idx, score) in enumerate(vector_results[:5], 1):
        chunk_id = engine.chunk_ids[idx]
        engineer = engine.metadatas[idx].get("engineer_name", "")
        project = engine.metadatas[idx].get("project_name", "")
        content_preview = engine.documents[idx][:100].replace("\n", " ")
        print(f"    {i}. [{score:.4f}] {chunk_id}")
        print(f"       {engineer} / {project}")
        print(f"       {content_preview}...")
    
    # Step 2: BM25 Search
    print("\n" + "=" * 80)
    print("[4/6] STEP 2: BM25 SEARCH (Keyword Matching)")
    print("=" * 80)
    bm25_results = engine._bm25_search(query, k=20)
    print(f"  Retrieved: {len(bm25_results)} candidates")
    print(f"\n  Top 5 BM25 Results:")
    for i, (idx, score) in enumerate(bm25_results[:5], 1):
        chunk_id = engine.chunk_ids[idx]
        engineer = engine.metadatas[idx].get("engineer_name", "")
        project = engine.metadatas[idx].get("project_name", "")
        content_preview = engine.documents[idx][:100].replace("\n", " ")
        print(f"    {i}. [{score:.4f}] {chunk_id}")
        print(f"       {engineer} / {project}")
        print(f"       {content_preview}...")
    
    # Step 3: Knowledge Graph Search
    print("\n" + "=" * 80)
    print("[4/6] STEP 3: KNOWLEDGE GRAPH SEARCH (Entity-Aware)")
    print("=" * 80)
    if engine.use_knowledge_graph and len(engine.knowledge_graph.engineers) > 0:
        # Extract entities
        entities = engine.knowledge_graph.extract_entities_from_query(query)
        print(f"  Extracted Entities:")
        for entity_type, entity_list in entities.items():
            if entity_list:
                print(f"    {entity_type}: {entity_list}")
        
        # Get all chunks for graph search
        all_chunks = []
        for idx in range(len(engine.chunk_ids)):
            all_chunks.append({
                "id": engine.chunk_ids[idx],
                "content": engine.documents[idx],
                "engineer_username": engine.metadatas[idx].get("engineer_username", ""),
                "project_name": engine.metadatas[idx].get("project_name", ""),
                "project_language": engine.metadatas[idx].get("project_language", ""),
                "project_framework": engine.metadatas[idx].get("project_framework", ""),
                "session_id": engine.metadatas[idx].get("session_id", "")
            })
        
        graph_results = engine.knowledge_graph.graph_search(query, all_chunks, limit=20)
        print(f"\n  Retrieved: {len(graph_results)} candidates")
        print(f"\n  Top 5 Graph Results:")
        for i, result in enumerate(graph_results[:5], 1):
            chunk_id = result.get("id", "")
            score = result.get("graph_score", 0)
            engineer = result.get("engineer_username", "")
            project = result.get("project_name", "")
            content_preview = result.get("content", "")[:100].replace("\n", " ")
            print(f"    {i}. [{score:.2f}] {chunk_id}")
            print(f"       {engineer} / {project}")
            print(f"       {content_preview}...")
    else:
        print("  Knowledge Graph not available or not built")
        graph_results = []
    
    # Step 4: Combine Scores
    print("\n" + "=" * 80)
    print("[5/6] STEP 4: COMBINING SCORES")
    print("=" * 80)
    if graph_results and engine.use_knowledge_graph:
        combined_results = engine._combine_scores_with_graph(
            vector_results, bm25_results, graph_results, k=20
        )
        print("  Method: Vector (70%) + BM25 (30%) + Graph (20% boost)")
    else:
        combined_results = engine._combine_scores(vector_results, bm25_results, k=20)
        print("  Method: Vector (70%) + BM25 (30%)")
    
    print(f"\n  Top 10 Combined Results (before reranking):")
    for i, (idx, score) in enumerate(combined_results[:10], 1):
        chunk_id = engine.chunk_ids[idx]
        engineer = engine.metadatas[idx].get("engineer_name", "")
        project = engine.metadatas[idx].get("project_name", "")
        
        # Get individual scores
        vector_score = dict(vector_results).get(idx, 0)
        bm25_score = dict(bm25_results).get(idx, 0)
        graph_score = 0
        if graph_results:
            chunk_id_to_score = {r.get("id"): r.get("graph_score", 0) for r in graph_results}
            graph_score = chunk_id_to_score.get(chunk_id, 0)
        
        print(f"    {i}. [{score:.4f}] {chunk_id} - {engineer}/{project}")
        print(f"       V:{vector_score:.3f} B:{bm25_score:.3f} G:{graph_score:.2f}")
    
    # Step 5: Format candidates for reranking
    print("\n" + "=" * 80)
    print("[6/6] STEP 5: RERANKING (Cross-Encoder)")
    print("=" * 80)
    candidates = []
    for idx, score in combined_results:
        candidates.append({
            "id": engine.chunk_ids[idx],
            "score": score,
            "content": engine.documents[idx],
            "engineer": {
                "username": engine.metadatas[idx].get("engineer_username", ""),
                "name": engine.metadatas[idx].get("engineer_name", ""),
                "role": engine.metadatas[idx].get("engineer_role", "")
            },
            "project": {
                "name": engine.metadatas[idx].get("project_name", ""),
                "language": engine.metadatas[idx].get("project_language", ""),
                "framework": engine.metadatas[idx].get("project_framework", "")
            },
            "session": {
                "id": engine.metadatas[idx].get("session_id", ""),
                "task": engine.metadatas[idx].get("session_task", ""),
                "timestamp": engine.metadatas[idx].get("timestamp", "")
            },
            "context": {
                "user_query": engine.metadatas[idx].get("user_query", ""),
                "assistant_response": engine.metadatas[idx].get("assistant_response", "")
            }
        })
    
    if engine.use_reranking:
        print(f"  Reranking {len(candidates)} candidates...")
        reranked = engine._rerank(query, candidates, top_k=limit)
        print(f"  ✓ Reranked to top {len(reranked)} results")
    else:
        reranked = candidates[:limit]
        print(f"  Reranking disabled, using top {limit} combined results")
    
    # Step 6: Final Results
    print("\n" + "=" * 80)
    print("FINAL RESULTS (After Reranking)")
    print("=" * 80)
    for i, result in enumerate(reranked[:limit], 1):
        print(f"\n  {i}. {result['id']}")
        print(f"     Engineer: {result['engineer']['name']} ({result['engineer']['role']})")
        print(f"     Project: {result['project']['name']} ({result['project']['language']})")
        print(f"     Task: {result['session']['task'][:60]}...")
        print(f"     Score: {result.get('score', 0):.4f}")
        if 'rerank_score' in result:
            print(f"     Rerank Score: {result['rerank_score']:.4f}")
        print(f"     Preview: {result['content'][:150].replace(chr(10), ' ')}...")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Query: '{query}'")
    print(f"  Expanded: '{expanded_query}'")
    print(f"  Vector candidates: {len(vector_results)}")
    print(f"  BM25 candidates: {len(bm25_results)}")
    print(f"  Graph candidates: {len(graph_results) if graph_results else 0}")
    print(f"  Combined candidates: {len(combined_results)}")
    print(f"  Final results: {len(reranked)}")
    print(f"  Reranking: {'Yes' if engine.use_reranking else 'No'}")
    print("=" * 80)


if __name__ == "__main__":
    # Test queries
    test_queries = [
        "video encoding optimization",
        "S3 multipart upload",
        "error handling in Python"
    ]
    
    if len(sys.argv) > 1:
        # Use command line query
        query = " ".join(sys.argv[1:])
        test_query(query, limit=5)
    else:
        # Test default queries
        for query in test_queries:
            test_query(query, limit=5)
            print("\n\n")

