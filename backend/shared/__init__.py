"""Shared utilities and models."""

from .data_loader import (
    load_session_files,
    create_searchable_chunks,
    get_unique_engineers,
    get_unique_projects,
    get_stats,
    build_full_sessions_index,
    get_session_detail,
    get_all_sessions_list,
    extract_engineer_name
)

from .models import (
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

__all__ = [
    "load_session_files",
    "create_searchable_chunks",
    "get_unique_engineers",
    "get_unique_projects",
    "get_stats",
    "build_full_sessions_index",
    "get_session_detail",
    "get_all_sessions_list",
    "extract_engineer_name",
    "SearchRequest",
    "SearchResponse",
    "EngineerListResponse",
    "ProjectListResponse",
    "StatsResponse",
    "EngineerInfo",
    "ProjectInfo",
    "SessionDetailResponse",
    "SessionsListResponse",
    "SessionSummary",
    "SimilarRequest",
    "AnalyticsResponse",
    "TopicCount",
    "EngineerActivity",
    "ConversationMessage"
]

