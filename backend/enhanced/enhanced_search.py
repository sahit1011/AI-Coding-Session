"""
Enhanced RAG Pipeline with Hybrid Search, Reranking, and Query Expansion.

Improvements:
1. Hybrid Search: BM25 (keyword) + Vector (semantic)
2. Cross-Encoder Reranking: Better final ranking
3. LLM-based Query Expansion: Groq API for intelligent expansion (free tier available)
4. Multi-Stage Retrieval: Coarse-to-fine approach
5. Persistent ChromaDB: No re-indexing on restart
6. Domain-Specific Embeddings: CodeBERT for coding conversations
"""

import time
import re
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import numpy as np
import chromadb
from chromadb.config import Settings
from chromadb import PersistentClient


class EnhancedSearchEngine:
    """
    Enhanced search engine with hybrid search and reranking.
    
    Combines:
    - BM25 for keyword matching
    - Vector search for semantic similarity
    - Cross-encoder reranking for final ordering
    """
    
    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-mpnet-base-v2",  # FIXED: Better for Q&A
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_reranking: bool = True,
        hybrid_weight: float = 0.7,  # 0.7 = 70% vector, 30% BM25
        groq_api_key: Optional[str] = None,  # FIXED: Groq API key (NOT Grok - that's a typo)
        use_groq_expansion: bool = True,      # FIXED: Use Groq for query expansion
        groq_model: str = "llama-3.1-8b-instant"  # Current Groq models: llama-3.1-8b-instant, llama-3.1-70b-versatile, mixtral-8x7b-32768
    ):
        """
        Initialize enhanced search engine.
        
        Args:
            embedding_model: Model for vector embeddings (default: all-mpnet-base-v2 for Q&A)
            reranker_model: Cross-encoder for reranking
            use_reranking: Whether to use reranking (slower but better)
            hybrid_weight: Weight for vector search (1-hybrid_weight for BM25)
            groq_api_key: Groq API key for LLM-based query expansion (get free key at https://console.groq.com)
            use_groq_expansion: Whether to use Groq API for query expansion
            groq_model: Groq model to use (llama-3.1-8b-instant, llama-3.1-70b-versatile, mixtral-8x7b-32768)
        
        Note: "Groq" (not "Grok") is the AI inference platform - https://groq.com
        """
        print(f"Loading embedding model: {embedding_model}...")
        
        # FIXED: Better error handling with retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Try to load as SentenceTransformer first
                self.embedding_model = SentenceTransformer(embedding_model)
                print("✓ Embedding model loaded successfully!")
                break
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"✗ Failed to load {embedding_model} (attempt {retry_count}/{max_retries}): {e}")
                    print(f"  Retrying in {retry_count} seconds...")
                    import time
                    time.sleep(retry_count)
                    continue
                else:
                    print(f"✗ All retries failed for {embedding_model}")
                    break
        
        if retry_count >= max_retries:
            # All retries failed, try fallback
            e = Exception("Max retries exceeded")
            # If it fails, try to wrap CodeBERT or other BERT models
            if "codebert" in embedding_model.lower():
                print(f"Wrapping CodeBERT for sentence-transformers...")
                try:
                    from sentence_transformers import models
                    from transformers import AutoModel, AutoTokenizer
                    
                    # Load CodeBERT tokenizer and model
                    tokenizer = AutoTokenizer.from_pretrained(embedding_model)
                    bert_model = AutoModel.from_pretrained(embedding_model)
                    
                    # Wrap in SentenceTransformer format
                    word_embedding_model = models.Transformer(embedding_model)
                    pooling_model = models.Pooling(
                        word_embedding_model.get_word_embedding_dimension(),
                        pooling_mode_mean_tokens=True,
                        pooling_mode_cls_token=False,
                        pooling_mode_max_tokens=False
                    )
                    
                    self.embedding_model = SentenceTransformer(modules=[word_embedding_model, pooling_model])
                    print("✓ CodeBERT wrapped and loaded successfully!")
                except Exception as e2:
                    print(f"Warning: Could not wrap CodeBERT ({e2}), falling back to all-MiniLM-L6-v2")
                    self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            else:
                print(f"Warning: Could not load {embedding_model} ({e}), falling back to all-MiniLM-L6-v2")
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        
        if use_reranking:
            print(f"Loading reranker: {reranker_model}...")
            self.reranker = CrossEncoder(reranker_model)
            print("Reranker loaded!")
        else:
            self.reranker = None
        
        self.use_reranking = use_reranking
        self.hybrid_weight = hybrid_weight
        self.use_groq_expansion = use_groq_expansion  # FIXED: Consistent naming
        
        # Groq API setup (fast inference for open-source LLMs)
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.groq_model = groq_model  # Model to use: llama-3.1-8b-instant, etc.
        
        if self.groq_api_key and use_groq_expansion:
            print(f"Groq API configured for query expansion (model: {self.groq_model})")
            print("  Note: Groq (not Grok) - https://groq.com")
            print("  Free tier available at https://console.groq.com")
        elif use_groq_expansion and not self.groq_api_key:
            print("Warning: Groq API key not found. Using fallback expansion.")
            print("  Get free API key at: https://console.groq.com")
            self.use_groq_expansion = False
        else:
            self.use_groq_expansion = False
        
        # Initialize persistent ChromaDB
        chroma_db_path = os.getenv("CHROMA_DB_PATH", "./chroma_db_enhanced")
        os.makedirs(chroma_db_path, exist_ok=True)
        
        self.chroma_client = PersistentClient(
            path=chroma_db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="coding_sessions_enhanced",
            metadata={"hnsw:space": "cosine"}
        )
        
        # BM25 index (will be built from documents)
        self.bm25: Optional[BM25Okapi] = None
        self.tokenized_docs: List[List[str]] = []
        
        # Document store (for in-memory operations)
        # FIXED: Don't store embeddings in memory - ChromaDB has them
        self.documents: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []
        # self.embeddings: List[List[float]] = []  # ← Removed to save memory
        self.chunk_ids: List[str] = []
    
    def index_chunks(self, chunks: List[Dict[str, Any]], force_reindex: bool = False) -> None:
        """
        Index chunks with both vector and BM25.
        
        Uses persistent ChromaDB - will skip indexing if data already exists.
        
        Args:
            chunks: List of chunk dictionaries
            force_reindex: If True, re-index even if collection exists
        """
        if not chunks:
            print("No chunks to index!")
            return
        
        # Check if collection already has data
        existing_count = self.collection.count()
        has_data = existing_count > 0
        
        if has_data and not force_reindex:
            print(f"Collection already has {existing_count} chunks. Loading metadata only...")
            # FIXED: Load only IDs, documents, and metadatas (NOT embeddings to save memory)
            existing_data = self.collection.get(include=["documents", "metadatas"])
            
            self.chunk_ids = existing_data["ids"]
            self.documents = existing_data["documents"]
            self.metadatas = existing_data["metadatas"]
            # Don't load embeddings - ChromaDB has them, no need to duplicate in memory
            
            # Rebuild BM25 index from loaded documents
            print("Rebuilding BM25 index from loaded documents...")
            self.tokenized_docs = [self._tokenize(doc) for doc in self.documents]
            self.bm25 = BM25Okapi(self.tokenized_docs)
            
            print(f"✓ Loaded {len(self.chunk_ids)} chunks from persistent storage")
            print(f"  Embeddings kept in ChromaDB (memory efficient)")
            return
        
        print(f"Indexing {len(chunks)} chunks with hybrid search...")
        start_time = time.time()
        
        # Clear existing data if re-indexing
        if has_data:
            print("Clearing existing collection for re-indexing...")
            try:
                self.chroma_client.delete_collection("coding_sessions_enhanced")
                self.collection = self.chroma_client.create_collection(
                    name="coding_sessions_enhanced",
                    metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                print(f"Warning: Could not clear collection: {e}")
        
        # Prepare documents
        self.documents = []
        self.metadatas = []
        self.chunk_ids = []
        
        for chunk in chunks:
            self.documents.append(chunk["content"])
            self.metadatas.append({
                "engineer_username": chunk.get("engineer_username", ""),
                "engineer_name": chunk.get("engineer_name", ""),
                "engineer_role": chunk.get("engineer_role", ""),
                "project_name": chunk.get("project_name", ""),
                "project_language": chunk.get("project_language", ""),
                "project_framework": chunk.get("project_framework", ""),
                "session_id": chunk.get("session_id", ""),
                "session_task": chunk.get("session_task", ""),
                "timestamp": chunk.get("timestamp", ""),
                "user_query": chunk.get("user_query", "")[:500],
                "assistant_response": chunk.get("assistant_response", "")[:1000]
            })
            self.chunk_ids.append(chunk["id"])
        
        # Generate vector embeddings
        # FIXED: Generate and store embeddings without keeping all in memory
        print("Generating vector embeddings...")
        embeddings = self.embedding_model.encode(
            self.documents,
            show_progress_bar=True,
            convert_to_numpy=True
        ).tolist()
        
        # Store in persistent ChromaDB
        print("Storing embeddings in persistent ChromaDB...")
        batch_size = 100
        for i in range(0, len(self.chunk_ids), batch_size):
            end_idx = min(i + batch_size, len(self.chunk_ids))
            self.collection.add(
                ids=self.chunk_ids[i:end_idx],
                embeddings=embeddings[i:end_idx],
                documents=self.documents[i:end_idx],
                metadatas=self.metadatas[i:end_idx]
            )
        
        # Clear embeddings from memory after storing
        del embeddings
        
        # Build BM25 index
        print("Building BM25 index...")
        self.tokenized_docs = [self._tokenize(doc) for doc in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)
        
        elapsed = time.time() - start_time
        print(f"✓ Indexed {len(chunks)} chunks in {elapsed:.2f}s (saved to persistent storage)")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25."""
        # Convert to lowercase and split on non-word characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _expand_query_groq(self, query: str) -> str:
        """
        Expand query using Groq API for intelligent expansion.
        
        Uses fast open-source LLMs (Llama, Mixtral, etc.) via Groq's inference platform.
        Free tier available at https://console.groq.com
        """
        if not self.groq_api_key:
            return self._expand_query_fallback(query)
        
        try:
            import requests
            
            # Groq API endpoint (OpenAI-compatible)
            url = "https://api.groq.com/openai/v1/chat/completions"
            
            prompt = f"""You are a technical search assistant. Expand this coding-related search query with:
1. Technical synonyms and related terms
2. Common variations developers use
3. Related concepts in software engineering

Query: "{query}"

Return ONLY the expanded query with additional relevant terms. Keep it concise (max 15 words total).
Do not include explanations, just the expanded query."""

            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.groq_model,  # llama3-8b-8192, mixtral-8x7b-32768, gemma-7b-it
                "messages": [
                    {"role": "system", "content": "You are a technical search assistant. Return only the expanded query, no explanations."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 50
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                expanded = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                
                # Clean up: remove quotes, newlines, etc.
                expanded = re.sub(r'["\']', '', expanded)
                expanded = re.sub(r'\n+', ' ', expanded)
                expanded = re.sub(r'^Expanded query:\s*', '', expanded, flags=re.IGNORECASE)
                expanded = expanded.strip()
                
                # Fallback if response is empty or too long
                if expanded and len(expanded.split()) <= 20:
                    return expanded
                else:
                    return self._expand_query_fallback(query)
            else:
                error_msg = response.text if hasattr(response, 'text') else str(response.status_code)
                print(f"Groq API error: {response.status_code} - {error_msg}. Using fallback.")
                return self._expand_query_fallback(query)
                
        except Exception as e:
            print(f"Groq API expansion failed: {e}. Using fallback.")
            return self._expand_query_fallback(query)
    
    def _expand_query_fallback(self, query: str) -> str:
        """
        Fallback query expansion using rule-based synonyms.
        Used when Groq API is unavailable or not configured.
        """
        # Improved synonym dictionary (no duplicates)
        synonyms = {
            "upload": ["transfer", "send", "post", "multipart"],
            "download": ["fetch", "retrieve", "get"],
            "error": ["exception", "failure", "issue", "bug"],
            "optimize": ["improve", "enhance", "speed", "performance"],
            "optimization": ["improvement", "enhancement", "performance"],
            "memory": ["RAM", "storage", "buffer", "cache"],
            "video": ["streaming", "media", "playback", "encoding"],
            "file": ["document", "data", "resource"],
            "large": ["big", "huge", "massive"],
            "handle": ["manage", "process", "deal"],
            "retry": ["retry logic", "retry mechanism"],
            "encoding": ["transcoding", "compression"],
            "streaming": ["stream", "live", "real-time"],
            "quality": ["bitrate", "resolution"],
            "signaling": ["handshake", "negotiation"],
        }
        
        words = re.findall(r'\b\w+\b', query.lower())
        expanded_list = list(words)  # Keep original order
        
        # Add synonyms (deduplicated)
        seen = set(words)
        for word in words:
            if word in synonyms:
                for synonym in synonyms[word][:2]:  # Max 2 synonyms per word
                    if synonym not in seen:
                        expanded_list.append(synonym)
                        seen.add(synonym)
        
        return " ".join(expanded_list)
    
    def _expand_query(self, query: str) -> str:
        """
        Main query expansion method - routes to Groq or fallback.
        """
        if self.use_groq_expansion and self.groq_api_key:
            return self._expand_query_groq(query)
        else:
            return self._expand_query_fallback(query)
    
    def _vector_search(
        self,
        query: str,
        k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[int, float]]:
        """
        Vector similarity search using ChromaDB.
        
        Returns: List of (chunk_id, score) tuples
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, convert_to_numpy=True).tolist()
        
        # Build where clause for filtering
        where_clause = None
        if filters:
            where_conditions = []
            for key, value in filters.items():
                if value:
                    where_conditions.append({key: value})
            
            if len(where_conditions) == 1:
                where_clause = where_conditions[0]
            elif len(where_conditions) > 1:
                where_clause = {"$and": where_conditions}
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where_clause,
            include=["metadatas", "distances"]
        )
        
        # Format results: (chunk_id, similarity_score)
        formatted_results = []
        
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # Convert distance to similarity (cosine distance -> similarity)
                similarity = 1 - distance
                
                # Find index in our chunk_ids list for compatibility
                try:
                    idx = self.chunk_ids.index(chunk_id)
                except ValueError:
                    # If not in list, skip (shouldn't happen)
                    continue
                
                formatted_results.append((idx, float(similarity)))
        
        return formatted_results
    
    def _bm25_search(
        self,
        query: str,
        k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[int, float]]:
        """
        BM25 keyword search with improved normalization.
        
        FIXED: Use sigmoid normalization instead of simple max normalization
        for better score distribution and handling of outliers.
        
        Returns: List of (index, score) tuples
        """
        if not self.bm25:
            return []
        
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Apply filters
        if filters:
            for i in range(len(scores)):
                for key, value in filters.items():
                    if value and self.metadatas[i].get(key, "") != value:
                        scores[i] = 0
        
        # IMPROVED: Better normalization using sigmoid
        # Maps unbounded BM25 scores to [0, 1] range
        def sigmoid_normalize(x, scale=1.0):
            """Sigmoid normalization: maps (-∞, ∞) to (0, 1)"""
            return 1 / (1 + np.exp(-x / scale))
        
        # Normalize using sigmoid
        if scores.max() > 0:
            # Use median of non-zero scores as scale factor for better normalization
            non_zero_scores = scores[scores > 0]
            if len(non_zero_scores) > 0:
                scale = float(np.median(non_zero_scores))
                # Apply sigmoid normalization
                normalized_scores = np.array([
                    sigmoid_normalize(s, scale=scale) for s in scores
                ])
                scores = normalized_scores
            else:
                # Fallback to simple max normalization
                scores = scores / scores.max()
        
        # Get top K
        top_indices = np.argsort(scores)[::-1][:k]
        results = [(int(idx), float(scores[idx])) for idx in top_indices]
        
        return results
    
    def _combine_scores(
        self,
        vector_results: List[Tuple[int, float]],
        bm25_results: List[Tuple[int, float]],
        k: int
    ) -> List[Tuple[int, float]]:
        """
        Combine vector and BM25 scores using weighted average.
        """
        # Create score dictionaries
        vector_scores = {idx: score for idx, score in vector_results}
        bm25_scores = {idx: score for idx, score in bm25_results}
        
        # Get all unique indices
        all_indices = set(vector_scores.keys()) | set(bm25_scores.keys())
        
        # Combine scores
        combined = {}
        for idx in all_indices:
            v_score = vector_scores.get(idx, 0)
            b_score = bm25_scores.get(idx, 0)
            combined[idx] = (
                self.hybrid_weight * v_score +
                (1 - self.hybrid_weight) * b_score
            )
        
        # Sort and return top K
        sorted_results = sorted(combined.items(), key=lambda x: -x[1])[:k]
        return sorted_results
    
    def _rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates using cross-encoder.
        
        Args:
            query: Search query
            candidates: List of candidate results
            top_k: Number of results to return
        
        Returns: Reranked results
        """
        if not self.reranker or not candidates:
            return candidates
        
        # Prepare pairs for reranking
        pairs = [(query, c["content"]) for c in candidates]
        
        # Get reranking scores
        rerank_scores = self.reranker.predict(pairs)
        
        # Sort by rerank scores
        reranked = sorted(
            zip(candidates, rerank_scores),
            key=lambda x: -x[1]
        )[:top_k]
        
        # Update scores and return
        results = []
        for candidate, rerank_score in reranked:
            candidate["rerank_score"] = float(rerank_score)
            candidate["score"] = float(rerank_score)  # Use rerank score as final
            results.append(candidate)
        
        return results
    
    def search(
        self,
        query: str,
        limit: int = 10,
        engineer: Optional[str] = None,
        project: Optional[str] = None,
        language: Optional[str] = None,
        use_reranking: Optional[bool] = None,
        expand_query: bool = True
    ) -> Dict[str, Any]:
        """
        Enhanced hybrid search with optional reranking.
        
        Args:
            query: Search query
            limit: Number of results
            engineer: Filter by engineer
            project: Filter by project
            language: Filter by language
            use_reranking: Override default reranking setting
            expand_query: Whether to expand query with synonyms
        
        Returns:
            Search results with scores and metadata
        """
        start_time = time.time()
        
        # Query expansion
        if expand_query:
            expanded_query = self._expand_query(query)
        else:
            expanded_query = query
        
        # Build filters
        filters = {}
        if engineer:
            filters["engineer_username"] = engineer
        if project:
            filters["project_name"] = project
        if language:
            filters["project_language"] = language
        
        # Stage 1: Retrieve MORE candidates for better reranking
        # FIXED: Best practice is to retrieve 5-10x the final limit, minimum 50
        # This gives the reranker more options to choose from
        should_rerank = use_reranking if use_reranking is not None else self.use_reranking
        
        if should_rerank:
            # Retrieve significantly more candidates for reranking
            retrieve_k = max(50, min(limit * 7, 100))  # Between 50-100 candidates
        else:
            retrieve_k = limit
        
        # Vector search
        vector_results = self._vector_search(expanded_query, k=retrieve_k, filters=filters)
        
        # BM25 search
        bm25_results = self._bm25_search(query, k=retrieve_k, filters=filters)
        
        # Combine scores
        combined_results = self._combine_scores(vector_results, bm25_results, k=retrieve_k)
        
        # Format candidates
        candidates = []
        for idx, score in combined_results:
            candidates.append({
                "id": self.chunk_ids[idx],
                "score": score,
                "content": self.documents[idx],
                "engineer": {
                    "username": self.metadatas[idx].get("engineer_username", ""),
                    "name": self.metadatas[idx].get("engineer_name", ""),
                    "role": self.metadatas[idx].get("engineer_role", "")
                },
                "project": {
                    "name": self.metadatas[idx].get("project_name", ""),
                    "language": self.metadatas[idx].get("project_language", ""),
                    "framework": self.metadatas[idx].get("project_framework", "")
                },
                "session": {
                    "id": self.metadatas[idx].get("session_id", ""),
                    "task": self.metadatas[idx].get("session_task", ""),
                    "timestamp": self.metadatas[idx].get("timestamp", "")
                },
                "context": {
                    "user_query": self.metadatas[idx].get("user_query", ""),
                    "assistant_response": self.metadatas[idx].get("assistant_response", "")
                }
            })
        
        # Stage 2: Rerank (fine)
        if should_rerank and len(candidates) > 0:
            candidates = self._rerank(query, candidates, top_k=limit)
        else:
            candidates = candidates[:limit]
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "results": candidates,
            "total": len(candidates),
            "query_time_ms": round(elapsed_ms, 2),
            "query_expanded": expanded_query if expand_query else None,
            "reranked": should_rerank
        }
    
    def find_similar(
        self,
        chunk_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Find similar chunks using ChromaDB vector similarity.
        """
        start_time = time.time()
        
        # Get chunk from ChromaDB
        try:
            chunk_data = self.collection.get(ids=[chunk_id], include=["embeddings", "metadatas"])
            if not chunk_data["ids"]:
                return {
                    "results": [],
                    "total": 0,
                    "query_time_ms": 0,
                    "error": "Chunk not found"
                }
            
            chunk_embedding = chunk_data["embeddings"][0]
            source_metadata = chunk_data["metadatas"][0] if chunk_data["metadatas"] else {}
            
        except Exception as e:
            return {
                "results": [],
                "total": 0,
                "query_time_ms": 0,
                "error": f"Error retrieving chunk: {str(e)}"
            }
        
        # Search for similar chunks (limit+1 to exclude source)
        results = self.collection.query(
            query_embeddings=[chunk_embedding],
            n_results=limit + 1,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results, excluding source chunk
        formatted_results = []
        
        if results["ids"] and results["ids"][0]:
            for i, result_id in enumerate(results["ids"][0]):
                # Skip the source chunk itself
                if result_id == chunk_id:
                    continue
                
                if len(formatted_results) >= limit:
                    break
                
                distance = results["distances"][0][i]
                similarity = 1 - distance
                metadata = results["metadatas"][0][i]
                
                formatted_results.append({
                    "id": result_id,
                    "score": float(similarity),
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

