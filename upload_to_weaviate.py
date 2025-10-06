#!/usr/bin/env python3
"""
Upload processed JSONL chunks to Weaviate vector database
"""

import json
import os
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

def create_weaviate_schema(weaviate_url: str = "http://localhost:8080") -> bool:
    """Create the DocumentChunk schema in Weaviate"""
    schema = {
        "class": "DocumentChunk",
        "description": "Enterprise document chunks for RAG",
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {
                "model": "text-embedding-3-small",  # Updated to supported model
                "type": "text"
            },
            "generative-openai": {
                "model": "gpt-3.5-turbo"
            }
        },
        "properties": [
            {
                "name": "text",
                "dataType": ["text"],
                "description": "The chunk content",
                "moduleConfig": {
                    "text2vec-openai": {
                        "skip": False,
                        "vectorizePropertyName": False
                    }
                }
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

def upload_chunks_batch(chunks: List[Dict], weaviate_url: str = "http://localhost:8080", batch_size: int = 100) -> int:
    """Upload chunks to Weaviate in batches"""
    uploaded = 0
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        objects = []
        
        for chunk in batch:
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
            objects.append(obj)
        
        try:
            response = requests.post(
                f"{weaviate_url}/v1/batch/objects",
                json={"objects": objects},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                uploaded += len(batch)
                print(f"✅ Uploaded batch {i//batch_size + 1}: {len(batch)} chunks (total: {uploaded})")
            else:
                print(f"❌ Failed to upload batch {i//batch_size + 1}: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Error uploading batch {i//batch_size + 1}: {e}")
            
        # Small delay to avoid overwhelming the API
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
    parser = argparse.ArgumentParser(description="Upload processed chunks to Weaviate")
    parser.add_argument("--chunks_dir", type=str, default="data/processed_chunks", 
                       help="Directory containing JSONL chunk files")
    parser.add_argument("--weaviate_url", type=str, default="http://localhost:8080",
                       help="Weaviate instance URL")
    parser.add_argument("--batch_size", type=int, default=50,
                       help="Batch size for uploads")
    
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
    
    # Upload chunks
    start_time = time.time()
    uploaded = upload_chunks_batch(chunks, args.weaviate_url, args.batch_size)
    duration = time.time() - start_time
    
    print(f"\n🎉 Upload complete!")
    print(f"📊 Uploaded: {uploaded}/{len(chunks)} chunks")
    print(f"⏱️  Duration: {duration:.1f}s")
    print(f"🔍 You can now query your documents via Weaviate!")

if __name__ == "__main__":
    main()