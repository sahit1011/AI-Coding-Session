"""
Enhanced Chunking Strategies for Better RAG Performance.

Available strategies:
1. Overlapping (RECOMMENDED for agent sessions) - Preserves conversation context
2. Hierarchical - Multi-level (fine + coarse chunks)
3. Enriched - Q+A pairs with surrounding context

Default: Overlapping (optimal for agent session retrieval)
"""

from typing import List, Dict, Any, Tuple


def create_overlapping_chunks(
    sessions_data: List[Dict[str, Any]],
    window_size: int = 3,
    overlap: int = 1
) -> List[Dict[str, Any]]:
    """
    Create overlapping chunks for better context preservation.
    
    Args:
        sessions_data: Raw session data
        window_size: Number of Q+A pairs per chunk
        overlap: Number of pairs to overlap between chunks
    
    Returns:
        List of chunks with overlap
    """
    from shared.data_loader import extract_engineer_name
    
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
            
            # Extract Q+A pairs
            qa_pairs = []
            i = 0
            while i < len(msgs):
                msg = msgs[i]
                
                if msg.get("type") == "user_query":
                    user_query = msg.get("content", "")
                    assistant_response = ""
                    
                    # Look for following assistant response(s)
                    j = i + 1
                    while j < len(msgs):
                        next_msg = msgs[j]
                        if next_msg.get("type") == "assistant_response":
                            assistant_response += next_msg.get("content", "") + "\n"
                            j += 1
                        elif next_msg.get("type") in ["tool_invocation", "tool_result"]:
                            j += 1
                        else:
                            break
                    
                    if user_query and assistant_response.strip():
                        qa_pairs.append({
                            "user_query": user_query,
                            "assistant_response": assistant_response.strip(),
                            "sequence": msg.get("sequenceNumber", 0)
                        })
                    
                    i = j
                else:
                    i += 1
            
            # Create overlapping chunks
            if len(qa_pairs) == 0:
                continue
            
            # FIXED: Create chunks with sliding window, ensuring we get MORE chunks than basic
            # Strategy: Create overlapping windows, but also ensure we don't skip any pairs
            start_idx = 0
            while start_idx < len(qa_pairs):
                end_idx = min(start_idx + window_size, len(qa_pairs))
                window_pairs = qa_pairs[start_idx:end_idx]
                
                # FIXED: Always create a chunk, even if window is smaller than window_size
                # This ensures we don't lose any pairs
                if len(window_pairs) == 0:
                    break
                
                # Combine Q+A pairs in window
                combined_content = []
                for pair in window_pairs:
                    combined_content.append(f"Question: {pair['user_query']}")
                    combined_content.append(f"Answer: {pair['assistant_response']}")
                
                content = "\n\n".join(combined_content)
                
                # Add context from previous chunk if available
                if start_idx > 0 and overlap > 0:
                    prev_pairs = qa_pairs[max(0, start_idx - overlap):start_idx]
                    context = []
                    for pair in prev_pairs:
                        context.append(f"[Previous] {pair['user_query'][:100]}...")
                    if context:
                        content = "Context: " + " | ".join(context) + "\n\n" + content
                
                chunk = {
                    "id": f"chunk_{chunk_id:04d}",
                    "content": content,
                    "chunk_type": "overlapping_qa_window",
                    "window_size": len(window_pairs),
                    "window_start": start_idx,
                    "window_end": end_idx - 1,
                    
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
                    "timestamp": session.get("startedAt", ""),
                    
                    # Display context (first Q+A pair for preview)
                    "user_query": window_pairs[0]["user_query"],
                    "assistant_response": window_pairs[0]["assistant_response"][:500] + "..." if len(window_pairs[0]["assistant_response"]) > 500 else window_pairs[0]["assistant_response"]
                }
                
                chunks.append(chunk)
                chunk_id += 1
                
                # FIXED: Move window with smaller step to create more chunks
                # If we're at the end, break to avoid infinite loop
                if start_idx + window_size - overlap >= len(qa_pairs):
                    # Create one more chunk with remaining pairs if any
                    if end_idx < len(qa_pairs):
                        start_idx = end_idx
                    else:
                        break
                else:
                    # Move window (with overlap) - smaller step creates more chunks
                    start_idx += window_size - overlap
    
    return chunks


def create_hierarchical_chunks(
    sessions_data: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Create hierarchical chunks at multiple levels.
    
    Returns:
        Tuple of (fine_chunks, coarse_chunks)
        - fine_chunks: Individual Q+A pairs (detailed)
        - coarse_chunks: Session summaries (overview)
    """
    from shared.data_loader import create_searchable_chunks, extract_engineer_name
    
    # Level 1: Fine-grained (individual Q+A pairs)
    fine_chunks = create_searchable_chunks(sessions_data)
    
    # Level 2: Coarse-grained (session summaries)
    coarse_chunks = []
    chunk_id = 0
    
    for engineer_data in sessions_data:
        engineer = engineer_data.get("engineer", {})
        projects = {p["id"]: p for p in engineer_data.get("projects", [])}
        sessions = {s["id"]: s for s in engineer_data.get("sessions", [])}
        messages = engineer_data.get("messages", [])
        
        session_messages = {}
        for msg in messages:
            session_id = msg.get("sessionId")
            if session_id not in session_messages:
                session_messages[session_id] = []
            session_messages[session_id].append(msg)
        
        for session_id, msgs in session_messages.items():
            session = sessions.get(session_id, {})
            project_id = session.get("projectId")
            project = projects.get(project_id, {})
            
            msgs.sort(key=lambda x: x.get("sequenceNumber", 0))
            
            # Extract all Q+A pairs for summary
            qa_summaries = []
            i = 0
            while i < len(msgs):
                msg = msgs[i]
                
                if msg.get("type") == "user_query":
                    user_query = msg.get("content", "")
                    assistant_response = ""
                    
                    j = i + 1
                    while j < len(msgs):
                        next_msg = msgs[j]
                        if next_msg.get("type") == "assistant_response":
                            assistant_response += next_msg.get("content", "") + "\n"
                            j += 1
                        elif next_msg.get("type") in ["tool_invocation", "tool_result"]:
                            j += 1
                        else:
                            break
                    
                    if user_query and assistant_response.strip():
                        qa_summaries.append({
                            "q": user_query[:150] + "..." if len(user_query) > 150 else user_query,
                            "a": assistant_response[:200] + "..." if len(assistant_response) > 200 else assistant_response
                        })
                    
                    i = j
                else:
                    i += 1
            
            if len(qa_summaries) == 0:
                continue
            
            # Create session summary
            summary_parts = [f"Session: {session.get('metadata', {}).get('taskDescription', 'Coding session')}"]
            summary_parts.append(f"Total Q+A pairs: {len(qa_summaries)}")
            summary_parts.append("\nKey Topics:")
            
            for idx, qa in enumerate(qa_summaries[:5], 1):  # Top 5 for summary
                summary_parts.append(f"{idx}. Q: {qa['q']}")
                summary_parts.append(f"   A: {qa['a']}")
            
            if len(qa_summaries) > 5:
                summary_parts.append(f"\n... and {len(qa_summaries) - 5} more Q+A pairs")
            
            content = "\n".join(summary_parts)
            
            coarse_chunk = {
                "id": f"coarse_{chunk_id:04d}",
                "content": content,
                "chunk_type": "session_summary",
                "qa_count": len(qa_summaries),
                
                "engineer_username": engineer.get("username", ""),
                "engineer_name": extract_engineer_name(engineer.get("username", "")),
                "engineer_role": engineer.get("role", ""),
                
                "project_name": project.get("name", ""),
                "project_language": project.get("metadata", {}).get("primaryLanguage", ""),
                "project_framework": project.get("metadata", {}).get("framework", ""),
                
                "session_id": session_id,
                "session_task": session.get("metadata", {}).get("taskDescription", ""),
                "timestamp": session.get("startedAt", ""),
                
                "user_query": qa_summaries[0]["q"] if qa_summaries else "",
                "assistant_response": qa_summaries[0]["a"] if qa_summaries else ""
            }
            
            coarse_chunks.append(coarse_chunk)
            chunk_id += 1
    
    return fine_chunks, coarse_chunks


def create_enriched_chunks(
    sessions_data: List[Dict[str, Any]],
    context_window: int = 2
) -> List[Dict[str, Any]]:
    """
    Create chunks with enriched context from surrounding Q+A pairs.
    
    Args:
        sessions_data: Raw session data
        context_window: Number of previous Q+A pairs to include as context
    
    Returns:
        List of enriched chunks
    """
    from shared.data_loader import create_searchable_chunks, extract_engineer_name
    
    # Get base chunks
    base_chunks = create_searchable_chunks(sessions_data)
    
    # Group chunks by session
    chunks_by_session = {}
    for chunk in base_chunks:
        session_id = chunk.get("session_id")
        if session_id not in chunks_by_session:
            chunks_by_session[session_id] = []
        chunks_by_session[session_id].append(chunk)
    
    # Enrich chunks with context
    enriched_chunks = []
    for session_id, session_chunks in chunks_by_session.items():
        for idx, chunk in enumerate(session_chunks):
            # Get previous chunks as context
            context_start = max(0, idx - context_window)
            context_chunks = session_chunks[context_start:idx]
            
            if context_chunks:
                context_text = "Previous context:\n"
                for ctx_chunk in context_chunks:
                    context_text += f"- {ctx_chunk['user_query'][:100]}...\n"
                
                # Prepend context to content
                enriched_content = context_text + "\n" + chunk["content"]
            else:
                enriched_content = chunk["content"]
            
            enriched_chunk = chunk.copy()
            enriched_chunk["content"] = enriched_content
            enriched_chunk["chunk_type"] = "enriched_qa_pair"
            enriched_chunk["context_count"] = len(context_chunks)
            
            enriched_chunks.append(enriched_chunk)
    
    return enriched_chunks

