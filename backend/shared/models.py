"""Pydantic models for API request/response schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime


# === Request Models ===

class SearchFilters(BaseModel):
    engineer: Optional[str] = None
    project: Optional[str] = None
    language: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    offset: int = 0  # FIXED: Added for pagination
    filters: Optional[SearchFilters] = None


# === Response Models ===

class EngineerInfo(BaseModel):
    username: str
    name: str
    role: str


class ProjectInfo(BaseModel):
    name: str
    language: str
    framework: str


class SessionInfo(BaseModel):
    id: str
    task: str
    timestamp: str


class SearchContext(BaseModel):
    user_query: str
    assistant_response: str


class SearchResult(BaseModel):
    id: str
    score: float
    content: str
    engineer: EngineerInfo
    project: ProjectInfo
    session: SessionInfo
    context: SearchContext


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    offset: int = 0  # FIXED: Pagination offset
    limit: int = 10  # FIXED: Pagination limit
    has_more: bool = False  # FIXED: Whether there are more results
    query_time_ms: float
    query_expanded: Optional[str] = None  # Expanded query if query expansion was used
    reranked: Optional[bool] = None  # Whether results were reranked
    distribution: Optional[Dict[str, Any]] = None  # FIXED: Fairness distribution stats


class EngineerListResponse(BaseModel):
    engineers: List[EngineerInfo]


class ProjectListResponse(BaseModel):
    projects: List[ProjectInfo]


class StatsResponse(BaseModel):
    total_chunks: int
    total_sessions: int
    total_engineers: int
    total_projects: int
    languages: List[str]
    frameworks: List[str]


# === Session Detail Models ===

class ConversationMessage(BaseModel):
    id: str
    type: str  # "user_query" or "assistant_response"
    content: str
    timestamp: str
    sequence: int


class SessionDetailResponse(BaseModel):
    session_id: str
    task: str
    started_at: str
    ended_at: str
    engineer: EngineerInfo
    project: ProjectInfo
    conversation: List[ConversationMessage]
    message_count: int


class SessionSummary(BaseModel):
    session_id: str
    task: str
    engineer: EngineerInfo
    project: ProjectInfo
    started_at: str
    message_count: int


class SessionsListResponse(BaseModel):
    sessions: List[SessionSummary]
    total: int


# === Similar Sessions Models ===

class SimilarRequest(BaseModel):
    chunk_id: str
    limit: int = 5


# === Analytics Models ===

class TopicCount(BaseModel):
    topic: str
    count: int


class EngineerActivity(BaseModel):
    engineer: EngineerInfo
    session_count: int
    message_count: int


class AnalyticsResponse(BaseModel):
    top_topics: List[TopicCount]
    engineer_activity: List[EngineerActivity]
    recent_sessions: List[SessionSummary]

