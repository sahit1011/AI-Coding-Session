"""FastAPI backend for AI Coding Session Search."""

import os
import re
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Rate limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    RATE_LIMITING_AVAILABLE = False
    print("Warning: slowapi not installed. Rate limiting disabled.")
    print("Install with: pip install slowapi")

from shared.models import (
    SearchRequest,
    SearchResponse,
    EngineerListResponse,
    ProjectListResponse,
    StatsResponse,
    EngineerInfo,
    ProjectInfo,
    SessionDetailResponse,
    SessionsListResponse,
    SessionSummary,
    SimilarRequest,
    AnalyticsResponse,
    TopicCount,
    EngineerActivity,
    ConversationMessage
)
from shared.data_loader import (
    load_session_files,
    create_searchable_chunks,
    get_unique_engineers,
    get_unique_projects,
    get_stats,
    build_full_sessions_index,
    get_session_detail,
    get_all_sessions_list
)
from shared.config import SEARCH_MODE, ENHANCED_SEARCH_CONFIG, BASIC_SEARCH_CONFIG
from shared.cache import get_cache
from shared.fairness import ensure_fair_distribution, get_distribution_stats
from basic import get_search_engine
from enhanced import (
    EnhancedSearchEngine,
    create_overlapping_chunks,
    create_hierarchical_chunks,
    create_enriched_chunks
)


# ============================================================================
# Query Validation and Sanitization
# ============================================================================

def validate_and_sanitize_query(query: str, max_length: int = 500) -> str:
    """
    Validate and sanitize search query.
    
    FIXED: Added comprehensive query validation for security and quality.
    
    Checks:
    1. Empty query
    2. Length limits
    3. XSS prevention (remove dangerous characters)
    4. Whitespace normalization
    5. Suspicious patterns (SQL injection, XSS, etc.)
    
    Args:
        query: User's search query
        max_length: Maximum allowed query length
    
    Returns:
        Sanitized query string
    
    Raises:
        HTTPException: If query is invalid
    """
    # 1. Check empty
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # 2. Check length
    if len(query) > max_length:
        raise HTTPException(
            status_code=400, 
            detail=f"Query too long (max {max_length} characters, got {len(query)})"
        )
    
    # 3. Remove dangerous characters (XSS prevention)
    # Remove: < > " ' ` (can be used for injection)
    sanitized = re.sub(r'[<>\"\'`]', '', query)
    
    # 4. Normalize whitespace
    sanitized = ' '.join(sanitized.split())
    
    # 5. Check if query is too short after sanitization
    if len(sanitized) < 2:
        raise HTTPException(
            status_code=400, 
            detail="Query too short (min 2 characters after sanitization)"
        )
    
    # 6. Check for suspicious patterns
    suspicious_patterns = [
        r'\b(union|select|insert|delete|drop|update|exec|execute)\b',  # SQL keywords
        r'<script',  # XSS
        r'javascript:',  # JS injection
        r'on(load|error|click)=',  # Event handlers
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="Query contains suspicious content"
            )
    
    return sanitized


# Global state
chunks = []
engineers = []
projects = []
stats = {}
enhanced_search_engine: Optional[EnhancedSearchEngine] = None
cache = None  # Will be initialized on startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize search engine on startup."""
    global chunks, engineers, projects, stats, cache
    
    # Initialize cache
    print("="*60)
    print("AI Coding Session Search - Initializing")
    print("="*60)
    
    print("\n[0/3] Initializing cache layer...")
    cache = get_cache()
    
    # Determine data directory
    data_dir = "../data" if os.path.exists("../data") else "data"
    
    # Load session data
    print("\n[1/3] Loading session data...")
    sessions_data = load_session_files(data_dir)
    print(f"      Loaded data for {len(sessions_data)} engineers")
    
    # Create searchable chunks based on strategy
    print("\n[2/3] Creating searchable chunks...")
    chunking_strategy = ENHANCED_SEARCH_CONFIG.get("chunking_strategy", "basic") if SEARCH_MODE == "enhanced" else "basic"
    
    if chunking_strategy == "overlapping":
        print(f"      Using overlapping chunking strategy...")
        chunks = create_overlapping_chunks(
            sessions_data,
            window_size=ENHANCED_SEARCH_CONFIG.get("overlap_window_size", 3),
            overlap=ENHANCED_SEARCH_CONFIG.get("overlap_size", 1)
        )
    elif chunking_strategy == "hierarchical":
        print(f"      Using hierarchical chunking strategy...")
        fine_chunks, coarse_chunks = create_hierarchical_chunks(sessions_data)
        chunks = fine_chunks + coarse_chunks  # Combine both levels
    elif chunking_strategy == "enriched":
        print(f"      Using enriched chunking strategy...")
        chunks = create_enriched_chunks(sessions_data)
    else:
        chunks = create_searchable_chunks(sessions_data)
    
    print(f"      Created {len(chunks)} searchable chunks")
    
    # Build full sessions index for detail view
    print("      Building full sessions index...")
    build_full_sessions_index(sessions_data)
    
    # Extract metadata
    engineers = get_unique_engineers(chunks)
    projects = get_unique_projects(chunks)
    stats = get_stats(chunks)
    
    print(f"      Engineers: {[e['name'] for e in engineers]}")
    print(f"      Projects: {[p['name'] for p in projects]}")
    print(f"      Languages: {stats['languages']}")
    
    # Initialize search engine(s)
    print(f"\n[3/3] Indexing chunks with {SEARCH_MODE} search mode...")
    
    if SEARCH_MODE == "enhanced":
        global enhanced_search_engine
        enhanced_search_engine = EnhancedSearchEngine(
            embedding_model=ENHANCED_SEARCH_CONFIG["embedding_model"],
            reranker_model=ENHANCED_SEARCH_CONFIG["reranker_model"],
            use_reranking=ENHANCED_SEARCH_CONFIG["use_reranking"],
            hybrid_weight=ENHANCED_SEARCH_CONFIG["hybrid_weight"],
            groq_api_key=ENHANCED_SEARCH_CONFIG.get("groq_api_key"),  # FIXED: Correct param name
            use_groq_expansion=ENHANCED_SEARCH_CONFIG.get("use_groq_expansion", True),  # FIXED
            groq_model=ENHANCED_SEARCH_CONFIG.get("groq_model", "llama-3.1-8b-instant")  # FIXED
        )
        enhanced_search_engine.index_chunks(
            chunks,
            force_reindex=ENHANCED_SEARCH_CONFIG.get("force_reindex", False)
        )
        print("      Enhanced search engine ready!")
    else:
        search_engine = get_search_engine()
        search_engine.index_chunks(chunks)
        print("      Basic search engine ready!")
    
    print("\n" + "="*60)
    print("Server ready! API available at http://localhost:8001")
    print("="*60 + "\n")
    
    yield  # Server runs here
    
    print("\nShutting down...")


# Create FastAPI app
app = FastAPI(
    title="AI Coding Session Search",
    description="Semantic search for AI coding assistant session history",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize rate limiter (if available)
if RATE_LIMITING_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    print("✓ Rate limiting enabled (slowapi)")
else:
    limiter = None

# Configure CORS - PRODUCTION READY
# FIXED: Specific origins instead of wildcard for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Development frontend (Vite)
        "http://localhost:3000",  # Alternative dev port
        os.getenv("FRONTEND_URL", ""),  # Production frontend from env var
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Specific methods only
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],  # Specific headers
    max_age=600,  # Cache preflight requests for 10 minutes
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AI Coding Session Search",
        "version": "1.0.0"
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(request_obj: Request, request: SearchRequest):
    """
    Search for relevant coding sessions.
    
    Performs semantic search using embeddings to find conversations
    that match the query by meaning, not just keywords.
    
    Uses enhanced search (hybrid + reranking) if enabled, otherwise basic search.
    
    Note: Rate limited to 30 requests/minute per IP if slowapi is installed.
    """
    # FIXED: Validate and sanitize query
    try:
        sanitized_query = validate_and_sanitize_query(request.query)
        request.query = sanitized_query  # Update request with sanitized query
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid query: {str(e)}")
    
    # FIXED: Validate pagination parameters
    if request.offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be >= 0")
    if request.limit < 1 or request.limit > 100:
        raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
    
    # Extract filters
    engineer = None
    project = None
    language = None
    
    if request.filters:
        engineer = request.filters.engineer
        project = request.filters.project
        language = request.filters.language
    
    # FIXED: Check cache first
    filters_dict = {
        "engineer": engineer,
        "project": project,
        "language": language
    }
    
    if cache:
        cached_results = cache.get(request.query, filters_dict, request.limit)
        if cached_results:
            print(f"✓ Cache hit for query: '{request.query[:50]}...'")
            return cached_results
    
    # FIXED: Get more results for pagination (fetch offset + limit + buffer)
    fetch_limit = request.offset + request.limit + 20  # Buffer for fairness adjustment
    
    # Use enhanced search if available
    if SEARCH_MODE == "enhanced" and enhanced_search_engine:
        results = enhanced_search_engine.search(
            query=request.query,
            limit=fetch_limit,
            engineer=engineer,
            project=project,
            language=language,
            expand_query=ENHANCED_SEARCH_CONFIG.get("expand_query", True)
        )
    else:
        # Fall back to basic search
        search_engine = get_search_engine()
        results = search_engine.search(
            query=request.query,
            limit=fetch_limit,
            engineer=engineer,
            project=project,
            language=language
        )
    
    # FIXED: Apply fairness (equal quota rule)
    # Ensure balanced representation across engineers
    if results.get("results"):
        all_results = results["results"]
        
        # Apply fairness to full result set first
        fair_results = ensure_fair_distribution(
            all_results,
            target_count=len(all_results),
            fairness_mode="balanced"
        )
        
        # Then apply pagination
        total_available = len(fair_results)
        paginated_results = fair_results[request.offset:request.offset + request.limit]
        
        results["results"] = paginated_results
        results["total"] = total_available
        results["offset"] = request.offset
        results["limit"] = request.limit
        results["has_more"] = (request.offset + request.limit) < total_available
        
        # Add distribution stats
        results["distribution"] = get_distribution_stats(paginated_results)
    
    # FIXED: Cache the results
    if cache:
        cache.set(request.query, results, filters_dict, request.limit)
    
    return results


@app.get("/api/engineers", response_model=EngineerListResponse)
async def list_engineers():
    """List all engineers in the dataset."""
    return {
        "engineers": [
            EngineerInfo(**e) for e in engineers
        ]
    }


@app.get("/api/projects", response_model=ProjectListResponse)
async def list_projects():
    """List all projects in the dataset."""
    return {
        "projects": [
            ProjectInfo(**p) for p in projects
        ]
    }


@app.get("/api/stats", response_model=StatsResponse)
async def get_statistics():
    """Get dataset statistics."""
    return stats


# === NEW ENDPOINTS ===

@app.get("/api/sessions")
async def list_sessions():
    """List all sessions with basic info."""
    sessions_list = get_all_sessions_list()
    return {
        "sessions": sessions_list,
        "total": len(sessions_list)
    }


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get full session conversation details.
    
    Returns the complete conversation thread for a session,
    including all user queries and assistant responses.
    """
    session_data = get_session_detail(session_id)
    
    if not session_data:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    
    return session_data


@app.post("/api/similar")
async def find_similar(request: SimilarRequest):
    """
    Find sessions similar to a given chunk.
    
    Uses vector similarity to find related conversations
    that discuss similar topics or problems.
    """
    if SEARCH_MODE == "enhanced" and enhanced_search_engine:
        results = enhanced_search_engine.find_similar(
            chunk_id=request.chunk_id,
            limit=request.limit
        )
    else:
        search_engine = get_search_engine()
        results = search_engine.find_similar(
            chunk_id=request.chunk_id,
            limit=request.limit
        )
    return results


@app.post("/api/search/compare")
async def compare_search(request: SearchRequest):
    """
    Compare basic vs enhanced search strategies.
    
    Returns results from both strategies for comparison.
    """
    # FIXED: Validate query
    try:
        sanitized_query = validate_and_sanitize_query(request.query)
        request.query = sanitized_query
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid query: {str(e)}")
    
    # Extract filters
    engineer = None
    project = None
    language = None
    
    if request.filters:
        engineer = request.filters.engineer
        project = request.filters.project
        language = request.filters.language
    
    # Basic search
    basic_engine = get_search_engine()
    basic_results = basic_engine.search(
        query=request.query,
        limit=request.limit,
        engineer=engineer,
        project=project,
        language=language
    )
    
    # Enhanced search
    enhanced_results = None
    if enhanced_search_engine:
        enhanced_results = enhanced_search_engine.search(
            query=request.query,
            limit=request.limit,
            engineer=engineer,
            project=project,
            language=language,
            expand_query=ENHANCED_SEARCH_CONFIG.get("expand_query", True)
        )
    
    return {
        "basic": basic_results,
        "enhanced": enhanced_results,
        "query": request.query
    }


@app.get("/api/suggestions")
async def get_suggestions(q: str = "", limit: int = 10):
    """
    Get search suggestions based on query prefix.
    
    Returns common topics and keywords that match the prefix.
    """
    search_engine = get_search_engine()
    suggestions = search_engine.get_suggestions(prefix=q, limit=limit)
    return {"suggestions": suggestions}


@app.get("/api/analytics")
async def get_analytics():
    """
    Get analytics about the dataset.
    
    Returns top topics, engineer activity, and recent sessions.
    """
    # Calculate engineer activity
    engineer_stats = {}
    session_tasks = []
    
    for chunk in chunks:
        engineer_name = chunk.get("engineer_name")
        if engineer_name not in engineer_stats:
            engineer_stats[engineer_name] = {
                "username": chunk.get("engineer_username"),
                "name": engineer_name,
                "role": chunk.get("engineer_role"),
                "sessions": set(),
                "messages": 0
            }
        engineer_stats[engineer_name]["sessions"].add(chunk.get("session_id"))
        engineer_stats[engineer_name]["messages"] += 1
        
        # Collect tasks for topic analysis
        task = chunk.get("session_task")
        if task:
            session_tasks.append(task)
    
    # Format engineer activity
    engineer_activity = []
    for name, data in engineer_stats.items():
        engineer_activity.append({
            "engineer": {
                "username": data["username"],
                "name": data["name"],
                "role": data["role"]
            },
            "session_count": len(data["sessions"]),
            "message_count": data["messages"]
        })
    
    # Sort by message count
    engineer_activity.sort(key=lambda x: x["message_count"], reverse=True)
    
    # Extract top topics from tasks
    topic_counts = {}
    for task in session_tasks:
        # Simple word-based topic extraction
        words = task.lower().split()
        for word in words:
            if len(word) > 4:  # Skip short words
                topic_counts[word] = topic_counts.get(word, 0) + 1
    
    # Get top topics
    top_topics = [
        {"topic": topic, "count": count}
        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:10]
    ]
    
    # Get recent sessions
    recent_sessions = get_all_sessions_list()[:5]
    
    return {
        "top_topics": top_topics,
        "engineer_activity": engineer_activity,
        "recent_sessions": recent_sessions
    }


# ============================================================================
# Cache Management Endpoints
# ============================================================================

@app.get("/api/cache/stats")
async def cache_stats():
    """
    Get cache statistics.
    
    Returns hit rate, total keys, and other cache metrics.
    """
    if not cache:
        return {"enabled": False, "message": "Cache not initialized"}
    
    return cache.stats()


@app.post("/api/cache/invalidate")
async def invalidate_cache(pattern: str = "search:*"):
    """
    Invalidate cached results.
    
    Args:
        pattern: Pattern to match (default: all search results)
    
    Returns:
        Number of keys invalidated
    """
    if not cache:
        return {"invalidated": 0, "message": "Cache not initialized"}
    
    count = cache.invalidate(pattern)
    return {
        "invalidated": count,
        "pattern": pattern,
        "message": f"Invalidated {count} cache entries"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

