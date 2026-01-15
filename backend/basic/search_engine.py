"""Semantic search engine using Sentence Transformers and ChromaDB."""

import time
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings


class SearchEngine:
    """
    Semantic search engine for AI coding sessions.
    
    Uses Sentence Transformers for embeddings and ChromaDB for vector storage.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the search engine.
        
        Args:
            model_name: Sentence Transformer model to use for embeddings.
                       all-MiniLM-L6-v2 is a good balance of speed and quality.
        """
        print(f"Loading embedding model: {model_name}...")
        
        # FIXED: Better error handling with retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.model = SentenceTransformer(model_name)
                print("✓ Model loaded successfully!")
                break
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"✗ Failed to load {model_name} (attempt {retry_count}/{max_retries}): {e}")
                    print(f"  Retrying in {retry_count} seconds...")
                    import time
                    time.sleep(retry_count)
                    continue
                else:
                    print(f"✗ All retries failed for {model_name}")
                    break
        
        if retry_count >= max_retries:
            # All retries failed, try fallback
            e = Exception("Max retries exceeded")
            # Try to wrap CodeBERT if it's a BERT model
            if "codebert" in model_name.lower():
                print(f"Wrapping CodeBERT for sentence-transformers...")
                try:
                    from sentence_transformers import models
                    
                    word_embedding_model = models.Transformer(model_name)
                    pooling_model = models.Pooling(
                        word_embedding_model.get_word_embedding_dimension(),
                        pooling_mode_mean_tokens=True
                    )
                    self.model = SentenceTransformer(modules=[word_embedding_model, pooling_model])
                    print("✓ CodeBERT wrapped and loaded successfully!")
                except Exception as e2:
                    print(f"Warning: Could not wrap CodeBERT ({e2}), falling back to all-MiniLM-L6-v2")
                    self.model = SentenceTransformer("all-MiniLM-L6-v2")
            else:
                print(f"Warning: Could not load {model_name} ({e}), falling back to all-MiniLM-L6-v2")
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Initialize ChromaDB with persistent storage
        import os
        chroma_db_path = os.getenv("CHROMA_DB_PATH", "./chroma_db")
        os.makedirs(chroma_db_path, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="coding_sessions",
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        self.chunks: List[Dict[str, Any]] = []
        self.model_name = model_name
    
    def index_chunks(self, chunks: List[Dict[str, Any]], force_reindex: bool = False) -> None:
        """
        Index chunks into the vector database.
        
        Args:
            chunks: List of chunk dictionaries with content and metadata.
            force_reindex: If True, re-index even if collection exists.
        """
        if not chunks:
            print("No chunks to index!")
            return
        
        self.chunks = chunks
        
        # Check if collection already has data
        existing_count = self.collection.count()
        has_data = existing_count > 0
        
        if has_data and not force_reindex:
            print(f"Collection already has {existing_count} chunks. Skipping indexing.")
            print("Set force_reindex=True to re-index.")
            return
        
        # Clear existing data if re-indexing
        if has_data:
            print("Clearing existing collection for re-indexing...")
            try:
                self.chroma_client.delete_collection("coding_sessions")
                self.collection = self.chroma_client.create_collection(
                    name="coding_sessions",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                print(f"Warning: Could not clear collection: {e}")
        
        print(f"Indexing {len(chunks)} chunks...")
        start_time = time.time()
        
        # Prepare data for ChromaDB
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]
        
        # Extract metadata (ChromaDB only supports string/int/float values)
        metadatas = []
        for chunk in chunks:
            metadatas.append({
                "engineer_username": chunk.get("engineer_username", ""),
                "engineer_name": chunk.get("engineer_name", ""),
                "engineer_role": chunk.get("engineer_role", ""),
                "project_name": chunk.get("project_name", ""),
                "project_language": chunk.get("project_language", ""),
                "project_framework": chunk.get("project_framework", ""),
                "session_id": chunk.get("session_id", ""),
                "session_task": chunk.get("session_task", ""),
                "timestamp": chunk.get("timestamp", ""),
                "user_query": chunk.get("user_query", "")[:500],  # Truncate for storage
                "assistant_response": chunk.get("assistant_response", "")[:1000]  # Truncate
            })
        
        # Generate embeddings and add to collection
        print("Generating embeddings...")
        # FIXED: Normalize embeddings for proper cosine distance calculation
        embeddings = self.model.encode(
            documents, 
            show_progress_bar=True,
            normalize_embeddings=True  # Normalize for cosine distance
        ).tolist()
        
        # Add in batches (ChromaDB handles this well, but let's be safe)
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end_idx = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:end_idx],
                embeddings=embeddings[i:end_idx],
                documents=documents[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
        
        elapsed = time.time() - start_time
        print(f"Indexed {len(chunks)} chunks in {elapsed:.2f}s")
    
    def search(
        self,
        query: str,
        limit: int = 10,
        engineer: Optional[str] = None,
        project: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search for relevant coding sessions.
        
        Args:
            query: Natural language search query.
            limit: Maximum number of results to return.
            engineer: Filter by engineer username (optional).
            project: Filter by project name (optional).
            language: Filter by programming language (optional).
        
        Returns:
            Dictionary with results, total count, and query time.
        """
        start_time = time.time()
        
        # Build where clause for filtering
        where_clause = None
        where_conditions = []
        
        if engineer:
            where_conditions.append({"engineer_username": engineer})
        if project:
            where_conditions.append({"project_name": project})
        if language:
            where_conditions.append({"project_language": language})
        
        if len(where_conditions) == 1:
            where_clause = where_conditions[0]
        elif len(where_conditions) > 1:
            where_clause = {"$and": where_conditions}
        
        # Generate query embedding
        # FIXED: Normalize query embedding for proper cosine distance
        query_embedding = self.model.encode(
            query,
            normalize_embeddings=True  # Normalize for cosine distance
        ).tolist()
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Convert distance to similarity score (cosine distance -> similarity)
                score = 1 - distance
                
                formatted_results.append({
                    "id": chunk_id,
                    "score": round(score, 4),
                    "content": results["documents"][0][i][:500] + "..." if len(results["documents"][0][i]) > 500 else results["documents"][0][i],
                    "engineer": {
                        "username": metadata.get("engineer_username", ""),
                        "name": metadata.get("engineer_name", ""),
                        "role": metadata.get("engineer_role", "")
                    },
                    "project": {
                        "name": metadata.get("project_name", ""),
                        "language": metadata.get("project_language", ""),
                        "framework": metadata.get("project_framework", "")
                    },
                    "session": {
                        "id": metadata.get("session_id", ""),
                        "task": metadata.get("session_task", ""),
                        "timestamp": metadata.get("timestamp", "")
                    },
                    "context": {
                        "user_query": metadata.get("user_query", ""),
                        "assistant_response": metadata.get("assistant_response", "")
                    }
                })
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "results": formatted_results,
            "total": len(formatted_results),
            "query_time_ms": round(elapsed_ms, 2)
        }
    
    def get_chunk_count(self) -> int:
        """Return the number of indexed chunks."""
        return self.collection.count()
    
    def find_similar(self, chunk_id: str, limit: int = 5) -> Dict[str, Any]:
        """
        Find chunks similar to a given chunk by its ID.
        
        Args:
            chunk_id: The ID of the chunk to find similar items for.
            limit: Maximum number of similar results to return.
        
        Returns:
            Dictionary with similar results and query time.
        """
        start_time = time.time()
        
        # Get the embedding for the given chunk
        try:
            result = self.collection.get(
                ids=[chunk_id],
                include=["embeddings", "metadatas", "documents"]
            )
            
            if result["embeddings"] is None or len(result["embeddings"]) == 0:
                return {"results": [], "total": 0, "query_time_ms": 0, "error": "Chunk not found"}
            
            chunk_embedding = result["embeddings"][0]
            if hasattr(chunk_embedding, 'tolist'):
                chunk_embedding = chunk_embedding.tolist()
            source_metadata = result["metadatas"][0] if result["metadatas"] else {}
            
        except Exception as e:
            return {"results": [], "total": 0, "query_time_ms": 0, "error": str(e)}
        
        # Search for similar chunks (limit + 1 to exclude the source chunk)
        results = self.collection.query(
            query_embeddings=[chunk_embedding],
            n_results=limit + 1,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results, excluding the source chunk
        formatted_results = []
        
        if results["ids"] and results["ids"][0]:
            for i, result_id in enumerate(results["ids"][0]):
                # Skip the source chunk itself
                if result_id == chunk_id:
                    continue
                
                if len(formatted_results) >= limit:
                    break
                    
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                score = 1 - distance
                
                formatted_results.append({
                    "id": result_id,
                    "score": round(score, 4),
                    "content": results["documents"][0][i][:500] + "..." if len(results["documents"][0][i]) > 500 else results["documents"][0][i],
                    "engineer": {
                        "username": metadata.get("engineer_username", ""),
                        "name": metadata.get("engineer_name", ""),
                        "role": metadata.get("engineer_role", "")
                    },
                    "project": {
                        "name": metadata.get("project_name", ""),
                        "language": metadata.get("project_language", ""),
                        "framework": metadata.get("project_framework", "")
                    },
                    "session": {
                        "id": metadata.get("session_id", ""),
                        "task": metadata.get("session_task", ""),
                        "timestamp": metadata.get("timestamp", "")
                    },
                    "context": {
                        "user_query": metadata.get("user_query", ""),
                        "assistant_response": metadata.get("assistant_response", "")
                    }
                })
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "results": formatted_results,
            "total": len(formatted_results),
            "query_time_ms": round(elapsed_ms, 2),
            "source_chunk": {
                "id": chunk_id,
                "engineer": source_metadata.get("engineer_name", ""),
                "project": source_metadata.get("project_name", "")
            }
        }
    
    def get_suggestions(self, prefix: str = "", limit: int = 10) -> List[str]:
        """
        Get search suggestions based on indexed content.
        Returns common topics/keywords from the dataset.
        """
        # Extract unique tasks and topics from chunks
        suggestions = set()
        
        if self.chunks:
            for chunk in self.chunks:
                task = chunk.get("session_task", "")
                if task and (not prefix or prefix.lower() in task.lower()):
                    suggestions.add(task)
        
        # Also add some common technical terms from content
        common_terms = [
            "video encoding", "file upload", "error handling", 
            "WebRTC", "streaming", "authentication", "API design",
            "performance optimization", "memory management", 
            "retry logic", "multipart upload", "quality selector",
            "picture in picture", "background playback"
        ]
        
        for term in common_terms:
            if not prefix or prefix.lower() in term.lower():
                suggestions.add(term)
        
        return sorted(list(suggestions))[:limit]


# Singleton instance for the application
_search_engine: Optional[SearchEngine] = None


def get_search_engine() -> SearchEngine:
    """Get or create the global search engine instance."""
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine


if __name__ == "__main__":
    # Test the search engine
    from data_loader import load_session_files, create_searchable_chunks
    import os
    
    # Adjust path for standalone testing
    data_dir = "../data" if os.path.exists("../data") else "data"
    
    # Load and index data
    sessions_data = load_session_files(data_dir)
    chunks = create_searchable_chunks(sessions_data)
    
    engine = SearchEngine()
    engine.index_chunks(chunks)
    
    # Test searches
    test_queries = [
        "how to handle large file uploads",
        "video encoding performance optimization",
        "WebRTC signaling",
        "React quality selector"
    ]
    
    print("\n" + "="*60)
    print("Testing search queries:")
    print("="*60)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = engine.search(query, limit=3)
        print(f"Found {results['total']} results in {results['query_time_ms']}ms")
        
        for result in results["results"]:
            print(f"  [{result['score']:.2f}] {result['engineer']['name']} - {result['project']['name']}")
            print(f"        Task: {result['session']['task'][:60]}...")

