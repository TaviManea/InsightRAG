#!/usr/bin/env python3
"""
Fixed upload script that ensures embeddings are generated
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, List
import argparse

def create_weaviate_schema(weaviate_url: str = "http://localhost:8080") -> bool:
    """Create the DocumentChunk schema with proper OpenAI configuration"""
    schema = {
        "class": "DocumentChunk",
        "description": "Enterprise document chunks for RAG",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {
                "model": "text-embedding-3-small",
                "type": "text"
            }
        },
        "properties": [
            {
                "name": "text",
                "dataType": ["text"],
                "description": "The chunk content"
            },
            {
                "name": "chunk_id",
                "dataType": ["string"],
                "description": "Unique chunk identifier"
            },
            {
                "name": "doc_id", 
                "dataType": ["string"],
                "description": "Document identifier"
            },
            {
                "name": "source",
                "dataType": ["string"],
                "description": "Source file path/URI"
            },
            {
                "name": "file_name",
                "dataType": ["string"], 
                "description": "Original file name"
            },
            {
                "name": "file_ext",
                "dataType": ["string"],
                "description": "File extension"
            },
            {
                "name": "role",
                "dataType": ["string"],
                "description": "Access role/permission level"
            },
            {
                "name": "chunk_index",
                "dataType": ["int"],
                "description": "Chunk position within document"
            },
            {
                "name": "ingested_at",
                "dataType": ["int"],
                "description": "Unix timestamp of ingestion"
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{weaviate_url}/v1/schema",
            json=schema,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            print("✅ Schema created successfully")
            return True
        elif response.status_code == 422 and "already exists" in response.text:
            print("ℹ️  Schema already exists")
            return True
        else:
            print(f"❌ Failed to create schema: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False

def upload_single_object(chunk: Dict, weaviate_url: str = "http://localhost:8080") -> bool:
    """Upload a single object and wait for embedding generation"""
    obj = {
        "class": "DocumentChunk",
        "properties": {
            "text": chunk["text"],
            "chunk_id": chunk["chunk_id"],
            "doc_id": chunk["doc_id"],
            "source": chunk["source"],
            "file_name": chunk["file_name"],
            "file_ext": chunk["file_ext"],
            "role": chunk["role"],
            "chunk_index": chunk["chunk_index"],
            "ingested_at": chunk["meta"]["ingested_at"]
        }
    }
    
    try:
        response = requests.post(
            f"{weaviate_url}/v1/objects",
            json=obj,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"❌ Failed to upload chunk {chunk['chunk_id']}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading chunk {chunk['chunk_id']}: {e}")
        return False

def upload_chunks_one_by_one(chunks: List[Dict], weaviate_url: str = "http://localhost:8080") -> int:
    """Upload chunks one by one to ensure embeddings are generated"""
    uploaded = 0
    
    for i, chunk in enumerate(chunks):
        if upload_single_object(chunk, weaviate_url):
            uploaded += 1
            if (i + 1) % 10 == 0:
                print(f"✅ Uploaded {i + 1}/{len(chunks)} chunks")
        
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    
    return uploaded

def load_all_chunks(chunks_dir: Path) -> List[Dict]:
    """Load all JSONL chunk files from the processed directory"""
    chunks = []
    
    for jsonl_file in chunks_dir.glob("*.jsonl"):
        print(f"📄 Loading {jsonl_file.name}...")
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            file_chunks = [json.loads(line) for line in f if line.strip()]
            chunks.extend(file_chunks)
            print(f"   → {len(file_chunks)} chunks")
    
    print(f"📊 Total chunks loaded: {len(chunks)}")
    return chunks

def main():
    parser = argparse.ArgumentParser(description="Upload processed chunks to Weaviate (fixed version)")
    parser.add_argument("--chunks_dir", type=str, default="data/processed_chunks", 
                       help="Directory containing JSONL chunk files")
    parser.add_argument("--weaviate_url", type=str, default="http://localhost:8080",
                       help="Weaviate instance URL")
    
    args = parser.parse_args()
    
    chunks_dir = Path(args.chunks_dir)
    if not chunks_dir.exists():
        print(f"❌ Chunks directory not found: {chunks_dir}")
        return
    
    print(f"🚀 Starting upload to Weaviate at {args.weaviate_url}")
    
    # Test connection
    try:
        response = requests.get(f"{args.weaviate_url}/v1/meta")
        if response.status_code != 200:
            print(f"❌ Cannot connect to Weaviate: {response.status_code}")
            return
        print("✅ Weaviate connection successful")
    except Exception as e:
        print(f"❌ Cannot connect to Weaviate: {e}")
        return
    
    # Create schema
    if not create_weaviate_schema(args.weaviate_url):
        print("❌ Failed to create schema, aborting")
        return
    
    # Load chunks
    chunks = load_all_chunks(chunks_dir)
    if not chunks:
        print("❌ No chunks found to upload")
        return
    
    # Upload chunks one by one (slower but more reliable)
    start_time = time.time()
    uploaded = upload_chunks_one_by_one(chunks, args.weaviate_url)
    duration = time.time() - start_time
    
    print(f"\n🎉 Upload complete!")
    print(f"📊 Uploaded: {uploaded}/{len(chunks)} chunks")
    print(f"⏱️  Duration: {duration:.1f}s")

if __name__ == "__main__":
    main()