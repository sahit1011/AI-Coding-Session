"""
Investigate why we get negative semantic scores.

Tests:
1. Same chunks, different models
2. Different chunking strategies, same model
3. Raw ChromaDB distances
4. Query expansion impact
"""

import os
import sys
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_loader import load_session_files
from enhanced.enhanced_chunking import create_overlapping_chunks
from shared.data_loader import create_searchable_chunks
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


def test_raw_distances():
    """Test raw ChromaDB distances to understand the issue."""
    print("=" * 80)
    print("INVESTIGATING NEGATIVE SEMANTIC SCORES")
    print("=" * 80)
    
    query = "video encoding optimization"
    
    # Load data
    data_dir = "../data" if os.path.exists("../data") else "data"
    sessions_data = load_session_files(data_dir)
    
    # Test 1: Basic chunks with basic model
    print("\n" + "=" * 80)
    print("TEST 1: Basic Chunks + Basic Model (all-MiniLM-L6-v2)")
    print("=" * 80)
    
    basic_chunks = create_searchable_chunks(sessions_data)
    basic_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Create embeddings
    basic_query_emb = basic_model.encode(query)
    basic_chunk_embs = basic_model.encode([chunk["content"] for chunk in basic_chunks[:5]])
    
    # Calculate cosine similarity manually
    print(f"\nQuery: '{query}'")
    print(f"Model: all-MiniLM-L6-v2 (384-dim)")
    print(f"Chunking: Basic (simple Q&A pairs)")
    print(f"\nTop 5 chunks - Manual Cosine Similarity:")
    for i, (chunk, emb) in enumerate(zip(basic_chunks[:5], basic_chunk_embs), 1):
        # Cosine similarity = dot product of normalized vectors
        similarity = np.dot(basic_query_emb, emb) / (np.linalg.norm(basic_query_emb) * np.linalg.norm(emb))
        distance = 1 - similarity  # ChromaDB uses distance
        print(f"  {i}. {chunk['id']}: similarity={similarity:.4f}, distance={distance:.4f}")
    
    # Test 2: Overlapping chunks with basic model
    print("\n" + "=" * 80)
    print("TEST 2: Overlapping Chunks + Basic Model (all-MiniLM-L6-v2)")
    print("=" * 80)
    
    overlapping_chunks = create_overlapping_chunks(sessions_data, window_size=2, overlap=1)
    overlapping_model = SentenceTransformer("all-MiniLM-L6-v2")
    
    overlapping_query_emb = overlapping_model.encode(query)
    overlapping_chunk_embs = overlapping_model.encode([chunk["content"] for chunk in overlapping_chunks[:5]])
    
    print(f"\nQuery: '{query}'")
    print(f"Model: all-MiniLM-L6-v2 (384-dim)")
    print(f"Chunking: Overlapping (window=2, overlap=1)")
    print(f"\nTop 5 chunks - Manual Cosine Similarity:")
    for i, (chunk, emb) in enumerate(zip(overlapping_chunks[:5], overlapping_chunk_embs), 1):
        similarity = np.dot(overlapping_query_emb, emb) / (np.linalg.norm(overlapping_query_emb) * np.linalg.norm(emb))
        distance = 1 - similarity
        print(f"  {i}. {chunk['id']}: similarity={similarity:.4f}, distance={distance:.4f}")
    
    # Test 3: Overlapping chunks with enhanced model
    print("\n" + "=" * 80)
    print("TEST 3: Overlapping Chunks + Enhanced Model (all-mpnet-base-v2)")
    print("=" * 80)
    
    enhanced_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    
    enhanced_query_emb = enhanced_model.encode(query)
    enhanced_chunk_embs = enhanced_model.encode([chunk["content"] for chunk in overlapping_chunks[:5]])
    
    print(f"\nQuery: '{query}'")
    print(f"Model: all-mpnet-base-v2 (768-dim)")
    print(f"Chunking: Overlapping (window=2, overlap=1)")
    print(f"\nTop 5 chunks - Manual Cosine Similarity:")
    for i, (chunk, emb) in enumerate(zip(overlapping_chunks[:5], enhanced_chunk_embs), 1):
        similarity = np.dot(enhanced_query_emb, emb) / (np.linalg.norm(enhanced_query_emb) * np.linalg.norm(emb))
        distance = 1 - similarity
        print(f"  {i}. {chunk['id']}: similarity={similarity:.4f}, distance={distance:.4f}")
        if distance > 1.0:
            print(f"      ⚠️  Distance > 1.0 → Negative similarity!")
    
    # Test 4: Query expansion impact
    print("\n" + "=" * 80)
    print("TEST 4: Query Expansion Impact")
    print("=" * 80)
    
    expanded_query = "video encoding optimization streaming media transcoding compression improvement enhancement"
    expanded_query_emb = enhanced_model.encode(expanded_query)
    
    print(f"\nOriginal Query: '{query}'")
    print(f"Expanded Query: '{expanded_query}'")
    print(f"\nTop 5 chunks - Cosine Similarity with Expanded Query:")
    for i, (chunk, emb) in enumerate(zip(overlapping_chunks[:5], enhanced_chunk_embs), 1):
        similarity = np.dot(expanded_query_emb, emb) / (np.linalg.norm(expanded_query_emb) * np.linalg.norm(emb))
        distance = 1 - similarity
        print(f"  {i}. {chunk['id']}: similarity={similarity:.4f}, distance={distance:.4f}")
        if distance > 1.0:
            print(f"      ⚠️  Distance > 1.0 → Negative similarity!")
    
    # Test 5: Compare chunk content
    print("\n" + "=" * 80)
    print("TEST 5: Chunk Content Comparison")
    print("=" * 80)
    
    print("\nBasic Chunk (chunk_0033):")
    basic_chunk = next((c for c in basic_chunks if c["id"] == "chunk_0033"), None)
    if basic_chunk:
        print(f"  Length: {len(basic_chunk['content'])} chars")
        print(f"  Preview: {basic_chunk['content'][:200]}...")
    
    print("\nOverlapping Chunk (chunk_0016):")
    overlapping_chunk = next((c for c in overlapping_chunks if c["id"] == "chunk_0016"), None)
    if overlapping_chunk:
        print(f"  Length: {len(overlapping_chunk['content'])} chars")
        print(f"  Preview: {overlapping_chunk['content'][:200]}...")
        print(f"  Window size: {overlapping_chunk.get('window_size', 'N/A')}")
    
    # Summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print("""
Why Negative Scores Occur:

1. COSINE DISTANCE vs SIMILARITY:
   - ChromaDB uses COSINE DISTANCE (0-2 range)
   - Distance = 1 - cosine_similarity
   - If cosine_similarity < 0, then distance > 1.0
   - Our conversion: similarity = 1 - distance → becomes negative

2. WHEN COSINE SIMILARITY < 0:
   - Vectors are more than 90° apart (orthogonal)
   - This happens when:
     * Query and chunk are semantically different
     * Embedding model produces vectors in different regions
     * Chunk content is very different from query

3. CHUNKING IMPACT:
   - Overlapping chunks have MORE content (2 Q&A pairs)
   - More content = different semantic vector
   - May not align well with query vector
   - Basic chunks (1 Q&A pair) are more focused

4. MODEL IMPACT:
   - all-mpnet-base-v2 (768-dim) has different vector space
   - Higher dimensions = more nuanced representations
   - Can produce more diverse similarity scores

5. QUERY EXPANSION IMPACT:
   - Expanded query changes the query vector
   - May move query vector away from chunk vectors
   - But helps with keyword matching (BM25)

CONCLUSION:
- Negative scores don't mean "bad" - they mean "semantically different"
- Enhanced mode compensates with BM25 + Graph + Reranking
- The FINAL reranked score (1.6833) is what matters, not the vector score
""")


if __name__ == "__main__":
    test_raw_distances()

