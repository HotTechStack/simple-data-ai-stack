#!/usr/bin/env python3
import sys
sys.path.append('/app')

from src.indexer import LightRAG
from src.validator import validate_knowledge_graph

def main():
    # Load existing RAG
    rag = LightRAG(working_dir="/app/data/lightrag")
    
    # Validate
    results = validate_knowledge_graph(rag)
    
    print(f"Validation Results:")
    print(f"  Entities: {results['entity_count']}")
    print(f"  Relations: {results['relation_count']}")
    print(f"  Orphan Nodes: {len(results['orphan_nodes'])}")
    print(f"  Accuracy: {results['extraction_accuracy']:.2%}")

if __name__ == "__main__":
    main()
