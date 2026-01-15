"""
Knowledge Graph for Enhanced Retrieval.

Extracts entities and relationships from agent sessions to enable:
- Entity-aware retrieval
- Multi-hop reasoning
- Relationship-based search
- Concept linking
"""

from typing import List, Dict, Any, Set, Tuple, Optional
import re
from collections import defaultdict


class KnowledgeGraph:
    """
    Knowledge graph for agent session retrieval.
    
    Entities:
    - Engineers (people)
    - Projects (codebases)
    - Technologies (languages, frameworks, tools)
    - Concepts (topics, patterns, solutions)
    
    Relationships:
    - Engineer -[works_on]-> Project
    - Project -[uses]-> Technology
    - Engineer -[discussed]-> Concept
    - Concept -[related_to]-> Concept
    - Session -[about]-> Concept
    """
    
    def __init__(self):
        self.engineers: Set[str] = set()
        self.projects: Set[str] = set()
        self.technologies: Set[str] = set()
        self.concepts: Set[str] = set()
        
        # Relationships: (source, relation, target)
        self.relationships: List[Tuple[str, str, str]] = []
        
        # Entity to chunks mapping
        self.entity_to_chunks: Dict[str, Set[str]] = defaultdict(set)
        
        # Common technology patterns
        self.tech_patterns = [
            r'\b(Python|Go|TypeScript|JavaScript|Swift|Java|Rust|C\+\+)\b',
            r'\b(React|Vue|Angular|Next\.js|FastAPI|Django|Flask|Chi|Gin)\b',
            r'\b(S3|AWS|Docker|Kubernetes|Redis|PostgreSQL|MongoDB)\b',
            r'\b(WebRTC|HLS|FFmpeg|Celery|RabbitMQ|Kafka)\b',
            r'\b(Git|GitHub|CI/CD|Jenkins|GitLab)\b'
        ]
        
        # Common concept patterns
        self.concept_patterns = [
            r'\b(encoding|streaming|upload|download|authentication|authorization)\b',
            r'\b(error handling|retry logic|rate limiting|caching)\b',
            r'\b(optimization|performance|scalability|memory management)\b',
            r'\b(multipart|chunking|segmentation|pipeline)\b',
            r'\b(validation|sanitization|security|encryption)\b'
        ]
    
    def build_from_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Build knowledge graph from chunks.
        
        Args:
            chunks: List of chunk dictionaries with metadata
        """
        print("Building knowledge graph from chunks...")
        
        for chunk in chunks:
            chunk_id = chunk.get("id", "")
            
            # Extract engineer
            engineer = chunk.get("engineer_username", "")
            if engineer:
                self.engineers.add(engineer)
                self.entity_to_chunks[engineer].add(chunk_id)
            
            # Extract project
            project = chunk.get("project_name", "")
            if project:
                self.projects.add(project)
                self.entity_to_chunks[project].add(chunk_id)
                
                # Engineer -[works_on]-> Project
                if engineer and project:
                    self.relationships.append((engineer, "works_on", project))
            
            # Extract technologies from project metadata
            language = chunk.get("project_language", "")
            framework = chunk.get("project_framework", "")
            
            if language:
                self.technologies.add(language)
                self.entity_to_chunks[language].add(chunk_id)
                if project:
                    self.relationships.append((project, "uses", language))
            
            if framework:
                self.technologies.add(framework)
                self.entity_to_chunks[framework].add(chunk_id)
                if project:
                    self.relationships.append((project, "uses", framework))
            
            # Extract technologies and concepts from content
            content = chunk.get("content", "")
            content_lower = content.lower()
            
            # Extract technologies from content
            for pattern in self.tech_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    tech = match.strip()
                    if len(tech) > 2:  # Filter out very short matches
                        self.technologies.add(tech)
                        self.entity_to_chunks[tech].add(chunk_id)
                        if project:
                            self.relationships.append((project, "uses", tech))
            
            # Extract concepts from content
            for pattern in self.concept_patterns:
                matches = re.findall(pattern, content_lower)
                for match in matches:
                    concept = match.strip()
                    if len(concept) > 2:
                        self.concepts.add(concept)
                        self.entity_to_chunks[concept].add(chunk_id)
                        
                        # Engineer -[discussed]-> Concept
                        if engineer:
                            self.relationships.append((engineer, "discussed", concept))
                        
                        # Session -[about]-> Concept
                        session_id = chunk.get("session_id", "")
                        if session_id:
                            self.relationships.append((session_id, "about", concept))
        
        # Build concept relationships (related concepts)
        self._build_concept_relationships(chunks)
        
        print(f"  ✓ Engineers: {len(self.engineers)}")
        print(f"  ✓ Projects: {len(self.projects)}")
        print(f"  ✓ Technologies: {len(self.technologies)}")
        print(f"  ✓ Concepts: {len(self.concepts)}")
        print(f"  ✓ Relationships: {len(self.relationships)}")
    
    def _build_concept_relationships(self, chunks: List[Dict[str, Any]]) -> None:
        """Build relationships between related concepts."""
        # Concepts that appear together in chunks are related
        concept_cooccurrence: Dict[Tuple[str, str], int] = defaultdict(int)
        
        for chunk in chunks:
            content_lower = chunk.get("content", "").lower()
            chunk_concepts = set()
            
            for pattern in self.concept_patterns:
                matches = re.findall(pattern, content_lower)
                for match in matches:
                    concept = match.strip()
                    if len(concept) > 2:
                        chunk_concepts.add(concept)
            
            # Count co-occurrences
            concepts_list = list(chunk_concepts)
            for i, concept1 in enumerate(concepts_list):
                for concept2 in concepts_list[i+1:]:
                    if concept1 != concept2:
                        pair = tuple(sorted([concept1, concept2]))
                        concept_cooccurrence[pair] += 1
        
        # Add relationships for frequently co-occurring concepts
        for (concept1, concept2), count in concept_cooccurrence.items():
            if count >= 2:  # At least 2 co-occurrences
                self.relationships.append((concept1, "related_to", concept2))
                self.relationships.append((concept2, "related_to", concept1))  # Bidirectional
    
    def extract_entities_from_query(self, query: str) -> Dict[str, List[str]]:
        """
        Extract entities from search query.
        
        Args:
            query: Search query string
        
        Returns:
            Dictionary with entity types and their values
        """
        query_lower = query.lower()
        entities = {
            "engineers": [],
            "projects": [],
            "technologies": [],
            "concepts": []
        }
        
        # Engineer name mappings (username -> display names)
        engineer_names = {
            "andrewwang": ["andrew wang", "andrew"],
            "daniellin": ["daniel lin", "daniel"],
            "dianalu": ["diana lu", "diana"]
        }
        
        # Check for engineers (with name variations)
        for engineer in self.engineers:
            engineer_lower = engineer.lower()
            engineer_display = engineer.replace("_", " ").lower()
            
            # Direct match
            if engineer_lower in query_lower or engineer_display in query_lower:
                entities["engineers"].append(engineer)
            # Check name mappings
            elif engineer in engineer_names:
                for name_variant in engineer_names[engineer]:
                    if name_variant in query_lower:
                        entities["engineers"].append(engineer)
                        break
        
        # Check for projects
        for project in self.projects:
            if project.lower() in query_lower:
                entities["projects"].append(project)
        
        # Check for technologies
        for tech in self.technologies:
            if tech.lower() in query_lower:
                entities["technologies"].append(tech)
        
        # Check for concepts
        for concept in self.concepts:
            if concept.lower() in query_lower:
                entities["concepts"].append(concept)
        
        return entities
    
    def find_related_entities(self, entity: str, relation_type: Optional[str] = None, max_depth: int = 2) -> Set[str]:
        """
        Find entities related to a given entity through graph traversal.
        
        Args:
            entity: Starting entity
            relation_type: Filter by relation type (optional)
            max_depth: Maximum traversal depth
        
        Returns:
            Set of related entity names
        """
        related = set()
        visited = set()
        queue = [(entity, 0)]  # (entity, depth)
        
        while queue:
            current, depth = queue.pop(0)
            
            if depth > max_depth or current in visited:
                continue
            
            visited.add(current)
            
            # Find relationships
            for source, relation, target in self.relationships:
                if relation_type and relation != relation_type:
                    continue
                
                if source == current and target not in visited:
                    related.add(target)
                    queue.append((target, depth + 1))
                elif target == current and source not in visited:
                    related.add(source)
                    queue.append((source, depth + 1))
        
        return related
    
    def get_chunks_by_entities(self, entities: List[str]) -> Set[str]:
        """
        Get chunk IDs associated with entities.
        
        Args:
            entities: List of entity names
        
        Returns:
            Set of chunk IDs
        """
        chunk_ids = set()
        for entity in entities:
            chunk_ids.update(self.entity_to_chunks.get(entity, set()))
        return chunk_ids
    
    def graph_search(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform graph-based retrieval.
        
        Args:
            query: Search query
            chunks: All available chunks
            limit: Maximum number of results
        
        Returns:
            List of chunks with graph-based scores
        """
        # Extract entities from query
        query_entities = self.extract_entities_from_query(query)
        
        # Find related entities through graph traversal
        all_related_entities = set()
        
        # Direct entities
        for entity_list in query_entities.values():
            all_related_entities.update(entity_list)
        
        # Related entities (1-hop)
        for entity_list in query_entities.values():
            for entity in entity_list:
                related = self.find_related_entities(entity, max_depth=1)
                all_related_entities.update(related)
        
        # Get chunks associated with entities
        relevant_chunk_ids = self.get_chunks_by_entities(list(all_related_entities))
        
        # Score chunks based on entity matches
        scored_chunks = []
        chunk_dict = {chunk["id"]: chunk for chunk in chunks}
        
        for chunk_id in relevant_chunk_ids:
            if chunk_id not in chunk_dict:
                continue
            
            chunk = chunk_dict[chunk_id]
            score = 0.0
            
            # Direct entity matches (higher score)
            for entity_type, entities in query_entities.items():
                if entity_type == "engineers" and chunk.get("engineer_username") in entities:
                    score += 2.0
                elif entity_type == "projects" and chunk.get("project_name") in entities:
                    score += 2.0
                elif entity_type == "technologies":
                    if chunk.get("project_language") in entities:
                        score += 1.5
                    if chunk.get("project_framework") in entities:
                        score += 1.5
                elif entity_type == "concepts":
                    content_lower = chunk.get("content", "").lower()
                    for concept in entities:
                        if concept.lower() in content_lower:
                            score += 1.0
            
            # Related entity matches (lower score)
            chunk_entities = set()
            chunk_entities.add(chunk.get("engineer_username", ""))
            chunk_entities.add(chunk.get("project_name", ""))
            chunk_entities.add(chunk.get("project_language", ""))
            chunk_entities.add(chunk.get("project_framework", ""))
            
            for entity in all_related_entities:
                if entity in chunk_entities:
                    score += 0.5
            
            if score > 0:
                chunk_copy = chunk.copy()
                chunk_copy["graph_score"] = score
                scored_chunks.append(chunk_copy)
        
        # Sort by graph score
        scored_chunks.sort(key=lambda x: x.get("graph_score", 0), reverse=True)
        
        return scored_chunks[:limit]

