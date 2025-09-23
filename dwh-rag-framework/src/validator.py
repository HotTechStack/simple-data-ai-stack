def validate_knowledge_graph(rag):
    """Validate knowledge graph quality"""
    
    results = {
        "entity_count": 0,
        "relation_count": 0,
        "orphan_nodes": [],
        "extraction_accuracy": 0.0
    }
    
    try:
        # Try to get graph if method exists
        if hasattr(rag, 'get_knowledge_graph'):
            graph = rag.get_knowledge_graph()
            results["entity_count"] = len(graph.nodes)
            results["relation_count"] = len(graph.edges)
            
            for node in graph.nodes:
                if graph.degree(node) == 0:
                    results["orphan_nodes"].append(node)
            
            if results["entity_count"] > 0:
                results["extraction_accuracy"] = (
                    results["entity_count"] - len(results["orphan_nodes"])
                ) / results["entity_count"]
        else:
            # LightRAG doesn't expose graph, return basic info
            results["message"] = "Knowledge graph validation not available for this RAG implementation"
    except Exception as e:
        results["error"] = str(e)
    
    return results