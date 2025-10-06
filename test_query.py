#!/usr/bin/env python3
"""
Test semantic search against your Weaviate document store
"""

import requests
import json

def test_semantic_search(query_text: str, limit: int = 5):
    """Test semantic search with a natural language query"""
    
    graphql_query = {
        "query": f"""
        {{
            Get {{
                DocumentChunk(
                    nearText: {{
                        concepts: ["{query_text}"]
                    }}
                    limit: {limit}
                ) {{
                    text
                    file_name
                    chunk_index
                    source
                    role
                    _additional {{
                        distance
                    }}
                }}
            }}
        }}
        """
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/v1/graphql", 
            json=graphql_query,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            chunks = result.get("data", {}).get("Get", {}).get("DocumentChunk", [])
            
            print(f"🔍 Query: '{query_text}'")
            print(f"📊 Found {len(chunks)} relevant chunks:\n")
            
            for i, chunk in enumerate(chunks, 1):
                distance = chunk.get("_additional", {}).get("distance", "N/A")
                print(f"--- Result {i} (distance: {distance}) ---")
                print(f"📄 File: {chunk['file_name']}")
                print(f"🔢 Chunk: {chunk['chunk_index']}")
                print(f"📝 Text: {chunk['text'][:200]}...")
                print()
                
        else:
            print(f"❌ Query failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error querying Weaviate: {e}")

if __name__ == "__main__":
    # Test with some telecom-related queries
    test_queries = [
        "5G network architecture",
        "telecom security threats",
        "AI in telecommunications",
        "network automation"
    ]
    
    for query in test_queries:
        test_semantic_search(query)
        print("="*60)