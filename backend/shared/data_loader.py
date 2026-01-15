"""Data loader for parsing Claude Code session JSON files."""

import json
import os
from typing import List, Dict, Any
from pathlib import Path


def load_session_files(data_dir: str = "data") -> List[Dict[str, Any]]:
    """Load all session JSON files from the data directory."""
    data_path = Path(data_dir)
    sessions_data = []
    
    for json_file in data_path.glob("*.json"):
        with open(json_file, 'r') as f:
            data = json.load(f)
            sessions_data.append(data)
    
    return sessions_data


def extract_engineer_name(username: str) -> str:
    """Convert username to display name."""
    name_map = {
        "andrewwang": "Andrew Wang",
        "daniellin": "Daniel Lin",
        "dianalu": "Diana Lu"
    }
    return name_map.get(username, username)


def create_searchable_chunks(sessions_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract searchable chunks from session data.
    
    FIXED: Improved message parsing to handle all assistant responses,
    even those that come after tool invocations/results.
    
    Chunk strategy: Pair user queries with assistant responses for semantic completeness.
    This ensures searches find complete conversations, not fragments.
    """
    chunks = []
    chunk_id = 0
    
    for engineer_data in sessions_data:
        engineer = engineer_data.get("engineer", {})
        projects = {p["id"]: p for p in engineer_data.get("projects", [])}
        sessions = {s["id"]: s for s in engineer_data.get("sessions", [])}
        messages = engineer_data.get("messages", [])
        
        # Group messages by session
        session_messages = {}
        for msg in messages:
            session_id = msg.get("sessionId")
            if session_id not in session_messages:
                session_messages[session_id] = []
            session_messages[session_id].append(msg)
        
        # Process each session
        for session_id, msgs in session_messages.items():
            session = sessions.get(session_id, {})
            project_id = session.get("projectId")
            project = projects.get(project_id, {})
            
            # Sort messages by sequence number
            msgs.sort(key=lambda x: x.get("sequenceNumber", 0))
            
            # Find user_query + assistant_response pairs
            i = 0
            while i < len(msgs):
                msg = msgs[i]
                
                if msg.get("type") == "user_query":
                    user_query = msg.get("content", "")
                    assistant_response = ""
                    
                    # FIXED: Look for ALL following assistant responses (even after tools)
                    # Continue through tool messages to find all responses
                    j = i + 1
                    while j < len(msgs):
                        next_msg = msgs[j]
                        msg_type = next_msg.get("type")
                        
                        if msg_type == "assistant_response":
                            assistant_response += next_msg.get("content", "") + "\n"
                            j += 1
                        elif msg_type in ["tool_invocation", "tool_result", "system_info"]:
                            # IMPORTANT: Continue looking for responses AFTER tool messages
                            j += 1
                        elif msg_type == "user_query":
                            # Stop at next user query
                            break
                        else:
                            # Unknown message type, skip but continue looking
                            j += 1
                    
                    # Create chunk if we have both query and response
                    if user_query.strip() and assistant_response.strip():
                        # Combine for searchable content
                        content = f"Question: {user_query}\n\nAnswer: {assistant_response.strip()}"
                        
                        chunk = {
                            "id": f"chunk_{chunk_id:04d}",
                            "content": content,
                            "chunk_type": "qa_pair",
                            
                            # Engineer metadata
                            "engineer_username": engineer.get("username", ""),
                            "engineer_name": extract_engineer_name(engineer.get("username", "")),
                            "engineer_role": engineer.get("role", ""),
                            
                            # Project metadata
                            "project_name": project.get("name", ""),
                            "project_language": project.get("metadata", {}).get("primaryLanguage", ""),
                            "project_framework": project.get("metadata", {}).get("framework", ""),
                            
                            # Session metadata
                            "session_id": session_id,
                            "session_task": session.get("metadata", {}).get("taskDescription", ""),
                            "timestamp": session.get("startedAt", msg.get("timestamp", "")),
                            
                            # Display context
                            "user_query": user_query,
                            "assistant_response": assistant_response.strip()
                        }
                        
                        chunks.append(chunk)
                        chunk_id += 1
                    
                    i = j  # Move past processed messages
                else:
                    i += 1
    
    return chunks


def get_unique_engineers(chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract unique engineers from chunks."""
    seen = set()
    engineers = []
    
    for chunk in chunks:
        username = chunk.get("engineer_username")
        if username and username not in seen:
            seen.add(username)
            engineers.append({
                "username": username,
                "name": chunk.get("engineer_name", ""),
                "role": chunk.get("engineer_role", "")
            })
    
    return sorted(engineers, key=lambda x: x["name"])


def get_unique_projects(chunks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract unique projects from chunks."""
    seen = set()
    projects = []
    
    for chunk in chunks:
        name = chunk.get("project_name")
        if name and name not in seen:
            seen.add(name)
            projects.append({
                "name": name,
                "language": chunk.get("project_language", ""),
                "framework": chunk.get("project_framework", "")
            })
    
    return sorted(projects, key=lambda x: x["name"])


def get_stats(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate dataset statistics."""
    engineers = set()
    projects = set()
    sessions = set()
    languages = set()
    frameworks = set()
    
    for chunk in chunks:
        engineers.add(chunk.get("engineer_username"))
        projects.add(chunk.get("project_name"))
        sessions.add(chunk.get("session_id"))
        if chunk.get("project_language"):
            languages.add(chunk.get("project_language"))
        if chunk.get("project_framework"):
            frameworks.add(chunk.get("project_framework"))
    
    return {
        "total_chunks": len(chunks),
        "total_sessions": len(sessions),
        "total_engineers": len(engineers),
        "total_projects": len(projects),
        "languages": sorted(list(languages)),
        "frameworks": sorted(list(frameworks))
    }


# Global store for full session data (populated on load)
_full_sessions_data: Dict[str, Any] = {}


def build_full_sessions_index(sessions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build an index of full session conversations for the session detail view.
    Returns a dict mapping session_id to full session info with all messages.
    """
    global _full_sessions_data
    
    for engineer_data in sessions_data:
        engineer = engineer_data.get("engineer", {})
        projects = {p["id"]: p for p in engineer_data.get("projects", [])}
        sessions = {s["id"]: s for s in engineer_data.get("sessions", [])}
        messages = engineer_data.get("messages", [])
        
        # Group messages by session
        session_messages = {}
        for msg in messages:
            session_id = msg.get("sessionId")
            if session_id not in session_messages:
                session_messages[session_id] = []
            session_messages[session_id].append(msg)
        
        # Build full session data
        for session_id, msgs in session_messages.items():
            session = sessions.get(session_id, {})
            project_id = session.get("projectId")
            project = projects.get(project_id, {})
            
            # Sort messages by sequence number
            msgs.sort(key=lambda x: x.get("sequenceNumber", 0))
            
            # Build conversation thread
            conversation = []
            for msg in msgs:
                msg_type = msg.get("type")
                
                # Only include user queries and assistant responses
                if msg_type in ["user_query", "assistant_response"]:
                    conversation.append({
                        "id": msg.get("id"),
                        "type": msg_type,
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "sequence": msg.get("sequenceNumber", 0)
                    })
            
            _full_sessions_data[session_id] = {
                "session_id": session_id,
                "task": session.get("metadata", {}).get("taskDescription", ""),
                "started_at": session.get("startedAt", ""),
                "ended_at": session.get("endedAt", ""),
                "engineer": {
                    "username": engineer.get("username", ""),
                    "name": extract_engineer_name(engineer.get("username", "")),
                    "role": engineer.get("role", "")
                },
                "project": {
                    "name": project.get("name", ""),
                    "language": project.get("metadata", {}).get("primaryLanguage", ""),
                    "framework": project.get("metadata", {}).get("framework", "")
                },
                "conversation": conversation,
                "message_count": len(conversation)
            }
    
    return _full_sessions_data


def get_session_detail(session_id: str) -> Dict[str, Any]:
    """Get full session details by session ID."""
    return _full_sessions_data.get(session_id)


def get_all_sessions_list() -> List[Dict[str, Any]]:
    """Get a list of all sessions with basic info."""
    sessions_list = []
    for session_id, session_data in _full_sessions_data.items():
        sessions_list.append({
            "session_id": session_id,
            "task": session_data["task"],
            "engineer": session_data["engineer"],
            "project": session_data["project"],
            "started_at": session_data["started_at"],
            "message_count": session_data["message_count"]
        })
    return sorted(sessions_list, key=lambda x: x["started_at"], reverse=True)


if __name__ == "__main__":
    # Test the data loader
    import sys
    
    # Adjust path for standalone testing
    data_dir = "../data" if os.path.exists("../data") else "data"
    
    print(f"Loading data from: {data_dir}")
    sessions_data = load_session_files(data_dir)
    print(f"Loaded {len(sessions_data)} engineer files")
    
    chunks = create_searchable_chunks(sessions_data)
    print(f"Created {len(chunks)} searchable chunks")
    
    # Show sample chunk
    if chunks:
        print("\nSample chunk:")
        sample = chunks[0]
        print(f"  ID: {sample['id']}")
        print(f"  Engineer: {sample['engineer_name']}")
        print(f"  Project: {sample['project_name']} ({sample['project_language']})")
        print(f"  Task: {sample['session_task']}")
        print(f"  Content preview: {sample['content'][:200]}...")
    
    # Show stats
    stats = get_stats(chunks)
    print(f"\nStats: {stats}")

