import requests
import json

def test_single_upload():
    """Test uploading a single document chunk"""
    
    # Test object
    test_chunk = {
        "class": "DocumentChunk",
        "properties": {
            "text": "This is a test chunk about 5G network architecture and telecommunications.",
            "chunk_id": "test_001",
            "doc_id": "test_doc",
            "source": "test.pdf",
            "file_name": "test.pdf",
            "file_ext": ".pdf",
            "role": "public",
            "chunk_index": 1,
            "ingested_at": 1696598400
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8080/v1/objects",
            json=test_chunk,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Upload response: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test upload successful!")
            
            # Now try to retrieve it
            query = {
                "query": """
                {
                    Get {
                        DocumentChunk(limit: 1) {
                            text
                            file_name
                        }
                    }
                }
                """
            }
            
            retrieve_response = requests.post("http://localhost:8080/v1/graphql", json=query)
            print(f"Retrieve response: {retrieve_response.json()}")
            
        else:
            print("❌ Test upload failed!")
            
    except Exception as e:
        print(f"❌ Error during test upload: {e}")

if __name__ == "__main__":
    test_single_upload()