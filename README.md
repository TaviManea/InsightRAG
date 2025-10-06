# InsightRAG - Enterprise Document Intelligence System

A powerful Retrieval-Augmented Generation (RAG) system for processing and querying enterprise documents using semantic search powered by OpenAI embeddings and Weaviate vector database.

## 🚀 Features

- **Multi-format Document Processing**: Supports PDF, DOCX, PPTX, XLSX, TXT, and Markdown files
- **Intelligent Text Chunking**: Semantic chunking with overlap for optimal retrieval
- **Vector Search**: OpenAI text-embedding-3-small for high-quality semantic search
- **Scalable Storage**: Weaviate vector database for fast similarity search
- **Metadata Preservation**: Tracks source files, chunk positions, and ingestion timestamps
- **Role-based Access**: Built-in support for access control and permissions
- **Robust Pipeline**: Error handling and progress tracking throughout the process

## 📋 Prerequisites

- Python 3.8+
- Docker (for Weaviate)
- OpenAI API key
- 4GB+ RAM recommended

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd InsightRAG
   ```

2. **Install Python dependencies**
   ```bash
   pip install requests python-docx python-pptx openpyxl PyPDF2 pathlib argparse
   ```

3. **Start Weaviate with OpenAI integration**
   ```bash
   docker run -d -p 8080:8080 \
     -e QUERY_DEFAULTS_LIMIT=25 \
     -e AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true \
     -e PERSISTENCE_DATA_PATH=/var/lib/weaviate \
     -e ENABLE_MODULES=text2vec-openai,generative-openai \
     -e OPENAI_APIKEY=your-openai-api-key-here \
     semitechnologies/weaviate:1.24.12
   ```

## 🏗️ Project Structure

```
InsightRAG/
├── data/
│   ├── raw_pdfs/              # Source documents
│   └── processed_chunks/      # Generated JSONL chunk files
├── ingest_documents.py        # Main document processing pipeline
├── upload_to_weaviate.py      # Upload chunks to vector database
├── upload_fixed.py            # Rate-limit resilient upload script
├── test_query.py              # Semantic search testing
├── debug_weaviate.py          # Database diagnostics
├── clear_schema.py            # Schema management utility
├── test_upload.py             # Upload testing utility
├── quick_test.py              # Quick connectivity tests
└── README.md
```

## 🔄 Usage Workflow

### 1. Document Ingestion

Process your documents into semantic chunks:

```bash
# Place your documents in data/raw_pdfs/
python ingest_documents.py --input_dir "data/raw_pdfs" --output_dir "data/processed_chunks"
```

**Supported formats**: PDF, DOCX, PPTX, XLSX, TXT, MD

### 2. Upload to Vector Database

Upload processed chunks to Weaviate:

```bash
# Standard upload (faster)
python upload_to_weaviate.py --chunks_dir "data/processed_chunks"

# Rate-limit resilient upload (for large datasets)
python upload_fixed.py --chunks_dir "data/processed_chunks"
```

### 3. Query Your Documents

Test semantic search capabilities:

```bash
python test_query.py
```

Example queries:
- "5G network architecture"
- "AI in telecommunications"
- "security threats and vulnerabilities"
- "network automation strategies"

## 🔧 Configuration

### Environment Variables
- `OPENAI_APIKEY`: Your OpenAI API key for embeddings
- `WEAVIATE_URL`: Weaviate instance URL (default: http://localhost:8080)

### Chunking Parameters
Modify in `ingest_documents.py`:
- `chunk_size`: Target characters per chunk (default: 1000)
- `overlap`: Character overlap between chunks (default: 200)

## 📊 Database Schema

The system creates a `DocumentChunk` class in Weaviate with:

```json
{
  "text": "string",           // Chunk content
  "chunk_id": "string",       // Unique identifier
  "doc_id": "string",         // Document identifier  
  "source": "string",         // File path
  "file_name": "string",      // Original filename
  "file_ext": "string",       // File extension
  "role": "string",           // Access role
  "chunk_index": "int",       // Position in document
  "ingested_at": "int"        // Unix timestamp
}
```

## 🛠️ Utilities

### Debug and Maintenance
```bash
# Check database status and object counts
python debug_weaviate.py

# Clear the schema (removes all data)
python clear_schema.py

# Test single object upload
python test_upload.py

# Quick connectivity test
python quick_test.py
```

## 📈 Performance

- **Processing Speed**: ~50-100 documents/minute (depends on size)
- **Upload Rate**: Limited by OpenAI API (40K tokens/minute)
- **Query Speed**: Sub-second semantic search
- **Storage**: ~1KB per chunk in Weaviate

## 🔍 Query Examples

The system excels at semantic queries across technical documents:

```python
# Example search results
"5G network architecture" → 3GPP specs, IEEE papers, technical documentation
"security vulnerabilities" → Security whitepapers, threat analysis
"AI applications" → ML/AI research papers, implementation guides
```

## 🚨 Troubleshooting

### Common Issues

1. **Rate Limit Errors (429)**
   - Use `upload_fixed.py` for slower, more reliable uploads
   - Check OpenAI usage limits and billing

2. **Empty Search Results**
   - Verify OpenAI API key is configured
   - Check if documents uploaded successfully with `debug_weaviate.py`

3. **Docker Connection Issues**
   - Ensure Weaviate container is running: `docker ps`
   - Check port 8080 availability

4. **Schema Conflicts**
   - Clear existing schema: `python clear_schema.py`
   - Restart the upload process

## 💰 Cost Estimates

- **OpenAI Embeddings**: ~$0.10 per 1M tokens
- **Typical Document**: 500-2000 tokens per chunk
- **Example**: 523 chunks ≈ $0.50-2.00 in embedding costs

## 🔐 Security Considerations

- Store OpenAI API keys securely (environment variables)
- Implement access controls for sensitive documents
- Consider on-premises deployment for confidential data
- Review document permissions before ingestion

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Weaviate** for the excellent vector database
- **OpenAI** for powerful embedding models
- **3GPP & IEEE** for the technical documentation used in examples

---

**Built for enterprise document intelligence and semantic search applications.**