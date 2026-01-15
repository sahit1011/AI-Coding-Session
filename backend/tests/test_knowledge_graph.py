"""
Test and Visualize Knowledge Graph for Agent Sessions.

This script:
1. Builds the knowledge graph from chunks
2. Visualizes entities and relationships
3. Shows statistics
4. Tests graph-based retrieval
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.data_loader import load_session_files
from enhanced.enhanced_chunking import create_overlapping_chunks
from enhanced.knowledge_graph import KnowledgeGraph

# Try to import visualization libraries
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    HAS_VIZ = True
except ImportError:
    HAS_VIZ = False
    print("Note: Install networkx and matplotlib for visualization:")
    print("  pip install networkx matplotlib")


def build_graph():
    """Build knowledge graph from data."""
    print("=" * 60)
    print("BUILDING KNOWLEDGE GRAPH")
    print("=" * 60)
    
    # Load data
    data_dir = "../data" if os.path.exists("../data") else "data"
    sessions_data = load_session_files(data_dir)
    print(f"\n✓ Loaded {len(sessions_data)} engineer files")
    
    # Create chunks
    chunks = create_overlapping_chunks(sessions_data, window_size=2, overlap=1)
    print(f"✓ Created {len(chunks)} overlapping chunks")
    
    # Build graph
    kg = KnowledgeGraph()
    kg.build_from_chunks(chunks)
    
    return kg, chunks


def print_graph_stats(kg: KnowledgeGraph):
    """Print knowledge graph statistics."""
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH STATISTICS")
    print("=" * 60)
    
    print(f"\n📊 Entities:")
    print(f"  Engineers: {len(kg.engineers)}")
    print(f"    {list(kg.engineers)}")
    print(f"\n  Projects: {len(kg.projects)}")
    print(f"    {list(kg.projects)}")
    print(f"\n  Technologies: {len(kg.technologies)}")
    print(f"    {sorted(list(kg.technologies))[:10]}...")  # Show first 10
    print(f"\n  Concepts: {len(kg.concepts)}")
    print(f"    {sorted(list(kg.concepts))[:10]}...")  # Show first 10
    
    print(f"\n🔗 Relationships: {len(kg.relationships)}")
    
    # Count by relationship type
    rel_counts = {}
    for source, relation, target in kg.relationships:
        rel_counts[relation] = rel_counts.get(relation, 0) + 1
    
    print(f"\n  By type:")
    for rel_type, count in sorted(rel_counts.items(), key=lambda x: -x[1]):
        print(f"    {rel_type}: {count}")
    
    # Show sample relationships
    print(f"\n  Sample relationships:")
    for i, (source, relation, target) in enumerate(kg.relationships[:10]):
        print(f"    {source} -[{relation}]-> {target}")
    if len(kg.relationships) > 10:
        print(f"    ... and {len(kg.relationships) - 10} more")
    
    # Entity to chunks mapping
    print(f"\n📦 Entity Coverage:")
    print(f"  Engineers with chunks: {len([e for e in kg.engineers if e in kg.entity_to_chunks])}")
    print(f"  Projects with chunks: {len([p for p in kg.projects if p in kg.entity_to_chunks])}")
    print(f"  Technologies with chunks: {len([t for t in kg.technologies if t in kg.entity_to_chunks])}")
    print(f"  Concepts with chunks: {len([c for c in kg.concepts if c in kg.entity_to_chunks])}")


def visualize_graph(kg: KnowledgeGraph):
    """Visualize knowledge graph."""
    if not HAS_VIZ:
        print("\n⚠️  Visualization libraries not available. Skipping graph visualization.")
        return
    
    print("\n" + "=" * 60)
    print("VISUALIZING KNOWLEDGE GRAPH")
    print("=" * 60)
    
    # Create NetworkX graph
    G = nx.MultiDiGraph()
    
    # Add nodes with types
    node_colors = []
    for engineer in kg.engineers:
        G.add_node(engineer, type="engineer")
        node_colors.append("lightblue")
    
    for project in kg.projects:
        G.add_node(project, type="project")
        node_colors.append("lightgreen")
    
    for tech in list(kg.technologies)[:20]:  # Limit for visualization
        G.add_node(tech, type="technology")
        node_colors.append("lightyellow")
    
    for concept in list(kg.concepts)[:15]:  # Limit for visualization
        G.add_node(concept, type="concept")
        node_colors.append("lightcoral")
    
    # Add edges
    edge_colors = []
    for source, relation, target in kg.relationships:
        if source in G and target in G:
            G.add_edge(source, target, relation=relation)
            # Color by relation type
            if relation == "works_on":
                edge_colors.append("blue")
            elif relation == "uses":
                edge_colors.append("green")
            elif relation == "discussed":
                edge_colors.append("orange")
            elif relation == "related_to":
                edge_colors.append("red")
            else:
                edge_colors.append("gray")
    
    if len(G.nodes()) == 0:
        print("⚠️  No nodes to visualize. Graph might be empty.")
        return
    
    # Create visualization with better layout
    plt.figure(figsize=(20, 16))
    
    # Use improved layout with more spacing
    pos = nx.spring_layout(G, k=3, iterations=100, seed=42)
    
    # Draw nodes by type with better sizing
    node_sizes = []
    final_node_colors = []
    for node in G.nodes():
        node_type = G.nodes[node].get('type', 'unknown')
        if node_type == 'engineer':
            node_sizes.append(2000)
            final_node_colors.append('#4A90E2')  # Blue
        elif node_type == 'project':
            node_sizes.append(1500)
            final_node_colors.append('#50C878')  # Green
        elif node_type == 'technology':
            node_sizes.append(800)
            final_node_colors.append('#FFD700')  # Gold
        else:  # concept
            node_sizes.append(600)
            final_node_colors.append('#FF6B6B')  # Coral
    
    nx.draw_networkx_nodes(G, pos, node_color=final_node_colors, 
                           node_size=node_sizes, alpha=0.8, linewidths=2, edgecolors='black')
    
    # Draw edges with better styling
    if len(edge_colors) > 0:
        nx.draw_networkx_edges(G, pos, edge_color=edge_colors[:len(G.edges())], 
                               alpha=0.4, arrows=True, arrowsize=15, width=1.5,
                               connectionstyle='arc3,rad=0.1')
    
    # Draw all labels with better formatting
    labels = {}
    for node in G.nodes():
        # Format labels for readability
        label = node.replace('_', ' ').title()
        if len(label) > 20:
            label = label[:17] + '...'
        labels[node] = label
    
    nx.draw_networkx_labels(G, pos, labels, font_size=7, font_weight='bold',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='none'))
    
    plt.title("Knowledge Graph: Entities and Relationships", fontsize=18, fontweight='bold', pad=20)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#4A90E2', label='Engineers'),
        Patch(facecolor='#50C878', label='Projects'),
        Patch(facecolor='#FFD700', label='Technologies'),
        Patch(facecolor='#FF6B6B', label='Concepts')
    ]
    plt.legend(handles=legend_elements, loc='upper left', fontsize=10)
    
    plt.axis('off')
    
    # Save visualization
    output_path = os.path.join(os.path.dirname(__file__), "knowledge_graph_visualization.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"\n✓ Graph visualization saved to: {output_path}")
    print(f"  Nodes: {len(G.nodes())}, Edges: {len(G.edges())}")
    
    # Also create a simpler subgraph visualization
    create_subgraph_visualization(kg, G)


def create_subgraph_visualization(kg: KnowledgeGraph, G: nx.MultiDiGraph):
    """Create a simpler subgraph focusing on engineers and projects."""
    if not HAS_VIZ:
        return
    
    # Create subgraph with only engineers and projects
    important_nodes = list(kg.engineers) + list(kg.projects)
    subgraph_nodes = [n for n in important_nodes if n in G]
    
    if len(subgraph_nodes) == 0:
        return
    
    subG = G.subgraph(subgraph_nodes).copy()
    
    # Add technologies connected to projects
    for project in kg.projects:
        if project in subG:
            # Find technologies used by this project
            for source, relation, target in kg.relationships:
                if source == project and relation == "uses" and target in G:
                    if target not in subG:
                        subG.add_node(target, type="technology")
                    subG.add_edge(source, target, relation=relation)
    
    plt.figure(figsize=(16, 12))
    
    # Better layout with more spacing
    pos = nx.spring_layout(subG, k=2.5, iterations=100, seed=42)
    
    # Color and size nodes by type
    node_colors = []
    node_sizes = []
    for node in subG.nodes():
        if node in kg.engineers:
            node_colors.append('#4A90E2')  # Blue
            node_sizes.append(2500)
        elif node in kg.projects:
            node_colors.append('#50C878')  # Green
            node_sizes.append(2000)
        else:
            node_colors.append('#FFD700')  # Gold
            node_sizes.append(1200)
    
    nx.draw_networkx_nodes(subG, pos, node_color=node_colors, 
                          node_size=node_sizes, alpha=0.9, linewidths=2.5, edgecolors='black')
    nx.draw_networkx_edges(subG, pos, alpha=0.5, arrows=True, arrowsize=20, width=2,
                          connectionstyle='arc3,rad=0.1')
    
    # Format labels
    labels = {}
    for node in subG.nodes():
        label = node.replace('_', ' ').title()
        if len(label) > 25:
            label = label[:22] + '...'
        labels[node] = label
    
    nx.draw_networkx_labels(subG, pos, labels, font_size=11, font_weight='bold',
                            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9, edgecolor='gray', linewidth=1))
    
    plt.title("Knowledge Graph: Engineers, Projects, and Technologies", 
              fontsize=16, fontweight='bold', pad=20)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#4A90E2', label='Engineers'),
        Patch(facecolor='#50C878', label='Projects'),
        Patch(facecolor='#FFD700', label='Technologies')
    ]
    plt.legend(handles=legend_elements, loc='upper left', fontsize=11)
    
    plt.axis('off')
    
    output_path = os.path.join(os.path.dirname(__file__), "knowledge_graph_simplified.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"✓ Simplified graph saved to: {output_path}")


def test_entity_extraction(kg: KnowledgeGraph):
    """Test entity extraction from queries."""
    print("\n" + "=" * 60)
    print("TESTING ENTITY EXTRACTION")
    print("=" * 60)
    
    test_queries = [
        "video encoding optimization",
        "Andrew's work on S3 uploads",
        "Python projects with error handling",
        "React streaming implementation",
        "multipart upload retry logic"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        entities = kg.extract_entities_from_query(query)
        
        if any(entities.values()):
            for entity_type, entity_list in entities.items():
                if entity_list:
                    print(f"  {entity_type}: {entity_list}")
        else:
            print("  No entities found")


def test_graph_retrieval(kg: KnowledgeGraph, chunks: list):
    """Test graph-based retrieval."""
    print("\n" + "=" * 60)
    print("TESTING GRAPH-BASED RETRIEVAL")
    print("=" * 60)
    
    test_queries = [
        "video encoding",
        "Andrew Wang",
        "S3 multipart upload",
        "error handling",
        "Python FastAPI"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        results = kg.graph_search(query, chunks, limit=5)
        
        print(f"  Found {len(results)} results:")
        for i, result in enumerate(results[:3], 1):
            chunk_id = result.get("id", "")
            score = result.get("graph_score", 0)
            engineer = result.get("engineer_username", "")
            project = result.get("project_name", "")
            print(f"    {i}. [{score:.2f}] {chunk_id} - {engineer}/{project}")


def test_relationship_traversal(kg: KnowledgeGraph):
    """Test relationship traversal."""
    print("\n" + "=" * 60)
    print("TESTING RELATIONSHIP TRAVERSAL")
    print("=" * 60)
    
    # Test finding related entities
    test_entities = [
        ("andrewwang", "engineer"),
        ("video-encoder", "project"),
        ("Python", "technology"),
        ("encoding", "concept")
    ]
    
    for entity, entity_type in test_entities:
        if entity in kg.engineers or entity in kg.projects or entity in kg.technologies or entity in kg.concepts:
            print(f"\n🔗 Entity: '{entity}' ({entity_type})")
            related = kg.find_related_entities(entity, max_depth=2)
            if related:
                print(f"  Related entities ({len(related)}):")
                for rel_entity in sorted(list(related))[:10]:
                    print(f"    - {rel_entity}")
                if len(related) > 10:
                    print(f"    ... and {len(related) - 10} more")
            else:
                print("  No related entities found")


def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("KNOWLEDGE GRAPH TESTING & VISUALIZATION")
    print("=" * 60)
    
    # Build graph
    kg, chunks = build_graph()
    
    # Print statistics
    print_graph_stats(kg)
    
    # Visualize
    visualize_graph(kg)
    
    # Test entity extraction
    test_entity_extraction(kg)
    
    # Test relationship traversal
    test_relationship_traversal(kg)
    
    # Test graph retrieval
    test_graph_retrieval(kg, chunks)
    
    print("\n" + "=" * 60)
    print("✅ TESTING COMPLETE")
    print("=" * 60)
    print("\nCheck the generated PNG files for graph visualizations!")


if __name__ == "__main__":
    main()

