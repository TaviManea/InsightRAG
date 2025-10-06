#!/usr/bin/env python3
"""
Enterprise Document Assistant – Ingestion Script
------------------------------------------------
Parses mixed-format enterprise documents (PDF, Word, PowerPoint, Excel, TXT/MD),
cleans & chunks text, and writes JSONL chunks with metadata for RAG pipelines.

Usage:
  python ingest_documents.py \
      --input ./data/raw_pdfs \
      --output ./data/processed_chunks \
      --chunk_size 500 \
      --chunk_overlap 50 \
      --role public

Notes:
- PDF extraction uses PyMuPDF (fitz). An optional lightweight OCR fallback using
  pytesseract is attempted only when a PDF page has no extractable text.
- Word/PPTX/Excel handled via python-docx, python-pptx, openpyxl.
- Designed to be dependency-light and portable. No LangChain required.
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# --------------------- Optional imports (handled gracefully) ------------------
def _safe_import(mod_name: str):
    try:
        return __import__(mod_name)
    except Exception as e:
        print(f"[warn] Optional module '{mod_name}' not available: {e}", file=sys.stderr)
        return None

fitz = _safe_import("fitz")  # PyMuPDF
docx = _safe_import("docx")  # python-docx
pptx = _safe_import("pptx")  # python-pptx
openpyxl = _safe_import("openpyxl")  # openpyxl
pytesseract = _safe_import("pytesseract")  # pytesseract
PIL = _safe_import("PIL")  # Pillow

# ----------------------------- Text utilities --------------------------------
WHITESPACE_RE = re.compile(r"[ \t]+")
NEWLINES_RE = re.compile(r"\n{3,}")
def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = WHITESPACE_RE.sub(" ", text)
    text = NEWLINES_RE.sub("\n\n", text)
    return text.strip()

def approximate_token_len(text: str) -> int:
    # Simple heuristic: ~1 token per 4 chars English-like text
    return max(1, len(text) // 4)

def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
    """
    Greedy paragraph-first chunker with overlap by approximate tokens.
    """
    if not text:
        return []
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = []
    cur_tokens = 0
    max_tokens = max(50, chunk_size)  # safety floor
    overlap_tokens = max(0, min(chunk_overlap, chunk_size // 2))

    def flush():
        nonlocal current, cur_tokens
        if current:
            chunks.append("\n\n".join(current).strip())
            current = []
            cur_tokens = 0

    for p in paras:
        p_tok = approximate_token_len(p)
        if cur_tokens + p_tok <= max_tokens:
            current.append(p)
            cur_tokens += p_tok
        else:
            # flush current
            flush()
            # if single paragraph too big, hard-wrap into subchunks
            if p_tok > max_tokens:
                words = p.split()
                buf, buf_tok = [], 0
                for w in words:
                    w_tok = approximate_token_len(w + " ")
                    if buf_tok + w_tok > max_tokens:
                        chunks.append(" ".join(buf).strip())
                        # overlap
                        if overlap_tokens > 0 and chunks[-1]:
                            back_words = chunks[-1].split()[-(overlap_tokens//2):]
                            buf = back_words[:]
                            buf_tok = approximate_token_len(" ".join(back_words) + " ")
                        else:
                            buf, buf_tok = [], 0
                    buf.append(w)
                    buf_tok += w_tok
                if buf:
                    chunks.append(" ".join(buf).strip())
            else:
                current = [p]
                cur_tokens = p_tok
    flush()

    # add overlap by merging tail of previous into next prefix (simple approach)
    if overlap_tokens > 0 and len(chunks) > 1:
        overlapped = []
        for i, ch in enumerate(chunks):
            if i == 0:
                overlapped.append(ch)
                continue
            prev = overlapped[-1]
            prev_tail_words = prev.split()[-overlap_tokens//2:] if prev else []
            merged = (" ".join(prev_tail_words) + " " + ch).strip() if prev_tail_words else ch
            overlapped.append(merged)
        chunks = overlapped

    # final cleanup
    return [normalize_whitespace(c) for c in chunks if c.strip()]

# --------------------------- Parsers per filetype -----------------------------
def parse_pdf(path: Path) -> str:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is required to parse PDFs.")
    text_parts: List[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            txt = page.get_text("text") or ""
            if not txt.strip() and pytesseract and PIL:
                # OCR fallback for image-only pages
                pix = page.get_pixmap(dpi=200)
                from PIL import Image  # type: ignore
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                try:
                    txt = pytesseract.image_to_string(img)
                except Exception as e:
                    print(f"[warn] OCR failed on {path.name} p{page.number}: {e}", file=sys.stderr)
            text_parts.append(txt)
    return normalize_whitespace("\n".join(text_parts))

def parse_docx(path: Path) -> str:
    if docx is None:
        raise RuntimeError("python-docx is required to parse .docx files.")
    document = docx.Document(str(path))
    paras = [p.text for p in document.paragraphs]
    return normalize_whitespace("\n".join(paras))

def parse_pptx(path: Path) -> str:
    if pptx is None:
        raise RuntimeError("python-pptx is required to parse .pptx files.")
    prs = pptx.Presentation(str(path))
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                texts.append(shape.text)
    return normalize_whitespace("\n".join(texts))

def parse_xlsx(path: Path) -> str:
    if openpyxl is None:
        raise RuntimeError("openpyxl is required to parse .xlsx files.")
    wb = openpyxl.load_workbook(filename=str(path), data_only=True)
    texts = []
    for ws in wb.worksheets:
        sheet_lines = []
        for row in ws.iter_rows(values_only=True):
            vals = [str(v) if v is not None else "" for v in row]
            if any(v.strip() for v in vals):
                sheet_lines.append(" | ".join(vals))
        if sheet_lines:
            texts.append(f"# Sheet: {ws.title}\n" + "\n".join(sheet_lines))
    return normalize_whitespace("\n\n".join(texts))

def parse_text_like(path: Path) -> str:
    try:
        data = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        data = path.read_text(encoding="latin-1", errors="ignore")
    return normalize_whitespace(data)

EXT_PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".pptx": parse_pptx,
    ".xlsx": parse_xlsx,
    ".xls": parse_xlsx,  # best effort; may require xlrd for old formats
    ".txt": parse_text_like,
    ".md": parse_text_like,
}

# ------------------------------ Main pipeline --------------------------------
def ingest_directory(
    input_dir: Path,
    output_dir: Path,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    default_role: str = "public",
    source_prefix: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Walk input_dir, parse supported files, chunk, write JSONL with metadata.
    Returns: (num_files, num_chunks)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    num_files = 0
    num_chunks = 0
    start_t = time.time()

    for root, _, files in os.walk(input_dir):
        for fname in files:
            ext = Path(fname).suffix.lower()
            parser = EXT_PARSERS.get(ext)
            if not parser:
                print(f"[skip] Unsupported extension: {fname}", file=sys.stderr)
                continue
            fpath = Path(root) / fname
            try:
                raw_text = parser(fpath)
            except Exception as e:
                print(f"[error] Failed to parse {fpath}: {e}", file=sys.stderr)
                continue

            if not raw_text.strip():
                print(f"[warn] Empty text after parsing: {fpath}", file=sys.stderr)
                continue

            chunks = chunk_text(raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            if not chunks:
                print(f"[warn] No chunks produced: {fpath}", file=sys.stderr)
                continue

            doc_id = str(uuid.uuid4())
            rel_path = str(fpath.relative_to(input_dir))
            source_uri = f"{source_prefix.rstrip('/')}/{rel_path}" if source_prefix else rel_path

            out_path = output_dir / f"{doc_id}.jsonl"
            with out_path.open("w", encoding="utf-8") as f:
                for i, ch in enumerate(chunks):
                    rec = {
                        "chunk_id": f"{doc_id}-{i}",
                        "doc_id": doc_id,
                        "source": source_uri,
                        "file_name": fname,
                        "file_ext": ext,
                        "role": default_role,
                        "chunk_index": i,
                        "text": ch,
                        "meta": {
                            "ingested_at": int(time.time()),
                            "relative_path": rel_path,
                        },
                    }
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

            num_files += 1
            num_chunks += len(chunks)
            print(f"[ok] {fname}: {len(chunks)} chunks -> {out_path.name}")

    dur = time.time() - start_t
    print(f"[done] Files: {num_files}, Chunks: {num_chunks}, Time: {dur:.1f}s")
    return num_files, num_chunks

def parse_args():
    p = argparse.ArgumentParser(description="Ingest and chunk enterprise documents into JSONL.")
    p.add_argument("--input", type=str, required=True, help="Input directory with raw files")
    p.add_argument("--output", type=str, required=True, help="Output directory for JSONL chunks")
    p.add_argument("--chunk_size", type=int, default=500, help="Approx token size per chunk")
    p.add_argument("--chunk_overlap", type=int, default=50, help="Approx token overlap between chunks")
    p.add_argument("--role", type=str, default="public", help="Default access role metadata")
    p.add_argument("--source_prefix", type=str, default=None, help="Optional URL/base path for 'source' field")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    in_dir = Path(args.input).resolve()
    out_dir = Path(args.output).resolve()
    if not in_dir.exists():
        print(f"[error] Input directory does not exist: {in_dir}", file=sys.stderr)
        sys.exit(1)
    ingest_directory(
        input_dir=in_dir,
        output_dir=out_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        default_role=args.role,
        source_prefix=args.source_prefix,
    )
