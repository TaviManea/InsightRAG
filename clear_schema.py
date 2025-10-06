import requests

def clear_schema():
    """Clear the DocumentChunk schema"""
    try:
        response = requests.delete("http://localhost:8080/v1/schema/DocumentChunk")
        if response.status_code == 200:
            print("✅ Schema cleared successfully")
        elif response.status_code == 404:
            print("ℹ️  Schema doesn't exist (already cleared)")
        else:
            print(f"❌ Failed to clear schema: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error clearing schema: {e}")

if __name__ == "__main__":
    clear_schema()