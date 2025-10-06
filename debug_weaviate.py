import requests
import json

def check_weaviate_status():
    """Debug Weaviate database status"""
    
    print("🔍 Checking Weaviate status...")
    
    # 1. Check schema
    try:
        response = requests.get("http://localhost:8080/v1/schema")
        if response.status_code == 200:
            schema = response.json()
            classes = schema.get("classes", [])
            print(f"✅ Schema classes found: {len(classes)}")
            for cls in classes:
                print(f"   - {cls['class']}: {len(cls.get('properties', []))} properties")
        else:
            print(f"❌ Schema check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return
    
    # 2. Count objects
    try:
        query = {
            "query": """
            {
                Aggregate {
                    DocumentChunk {
                        meta {
                            count
                        }
                    }
                }
            }
            """
        }
        response = requests.post("http://localhost:8080/v1/graphql", json=query)
        if response.status_code == 200:
            result = response.json()
            count = result.get("data", {}).get("Aggregate", {}).get("DocumentChunk", [{}])[0].get("meta", {}).get("count", 0)
            print(f"📊 Total DocumentChunk objects: {count}")
        else:
            print(f"❌ Count query failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error counting objects: {e}")
    
    # 3. Get raw objects (without vector search)
    try:
        query = {
            "query": """
            {
                Get {
                    DocumentChunk(limit: 3) {
                        text
                        file_name
                        chunk_id
                        doc_id
                    }
                }
            }
            """
        }
        response = requests.post("http://localhost:8080/v1/graphql", json=query)
        if response.status_code == 200:
            result = response.json()
            chunks = result.get("data", {}).get("Get", {}).get("DocumentChunk", [])
            print(f"📝 Sample objects retrieved: {len(chunks)}")
            for i, chunk in enumerate(chunks):
                print(f"   {i+1}. {chunk.get('file_name', 'Unknown')} - {chunk.get('chunk_id', 'No ID')}")
                print(f"      Text preview: {chunk.get('text', 'No text')[:100]}...")
        else:
            print(f"❌ Raw query failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error with raw query: {e}")
    
    # 4. Check if OpenAI module is working
    try:
        response = requests.get("http://localhost:8080/v1/modules")
        if response.status_code == 200:
            modules = response.json()
            print(f"🔧 Available modules: {list(modules.keys())}")
            
            openai_module = modules.get("text2vec-openai", {})
            if openai_module:
                print(f"   - OpenAI module status: {openai_module.get('status', 'Unknown')}")
            else:
                print("   - ❌ OpenAI module not found")
        else:
            print(f"❌ Modules check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking modules: {e}")

if __name__ == "__main__":
    check_weaviate_status()