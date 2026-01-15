"""
Configuration for RAG Pipeline.

Toggle between basic and enhanced search modes.
"""

import os

# Search mode: "basic" or "enhanced"
SEARCH_MODE = os.getenv("SEARCH_MODE", "enhanced")  # Default to enhanced

# Enhanced search settings
ENHANCED_SEARCH_CONFIG = {
    # FIXED: Use all-mpnet-base-v2 instead of CodeBERT
    # Reason: Better for conversational Q&A with code snippets
    # CodeBERT is for code-to-code similarity, not text similarity
    "embedding_model": "sentence-transformers/all-mpnet-base-v2",  # Best quality for Q&A
    # Alternative options:
    # - "all-MiniLM-L6-v2" (faster, slightly lower quality, 384-dim)
    # - "sentence-transformers/all-roberta-large-v1" (best quality, slower, 1024-dim)
    # - "microsoft/codebert-base" (for pure code, not recommended for Q&A)
    
    "reranker_model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "use_reranking": True,
    "hybrid_weight": 0.7,  # 70% vector, 30% BM25
    "expand_query": True,
    "use_groq_expansion": True,  # FIXED: Use Groq API for query expansion (free tier available)
    "groq_api_key": os.getenv("GROQ_API_KEY"),  # FIXED: Removed GROK_API_KEY typo
    "groq_model": "llama-3.1-8b-instant",  # Current models: llama-3.1-8b-instant, llama-3.1-70b-versatile, mixtral-8x7b-32768
    "chunking_strategy": "overlapping",  # "basic", "overlapping", "hierarchical", "enriched"
    "overlap_window_size": 3,
    "overlap_size": 1,
    "force_reindex": os.getenv("FORCE_REINDEX", "false").lower() == "true",  # Force re-indexing
}

# Basic search settings (for comparison)
BASIC_SEARCH_CONFIG = {
    "embedding_model": "all-MiniLM-L6-v2",
    "use_reranking": False,
    "hybrid_weight": 1.0,  # 100% vector, 0% BM25
    "expand_query": False,
    "chunking_strategy": "basic",
}

# Evaluation settings
EVALUATION_ENABLED = os.getenv("EVALUATION_ENABLED", "false").lower() == "true"

# Performance settings
BATCH_SIZE = 100
MAX_RESULTS = 50
RERANK_TOP_K = 20  # Rerank top 20, return top 10

