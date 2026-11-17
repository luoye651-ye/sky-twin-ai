"""Owner-scoped uploaded knowledge; local embedding, no automatic external calls."""
from io import BytesIO
from pathlib import Path
import re
import zipfile
from xml.etree import ElementTree

import numpy as np
from rag import local_embeddings
from safety_policy import is_secret_request

MAX_FILE = 2 * 1024 * 1024


def extract(name, data):
    if not data or len(data) > MAX_FILE:
        raise ValueError('文档须为1字节～2MiB')
    suffix = Path(name).suffix.lower()
    if suffix in ('.md', '.txt'):
        text = data.decode('utf-8-sig')
    elif suffix == '.docx':
        with zipfile.ZipFile(BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 10 * MAX_FILE:
                raise ValueError('DOCX解压大小超过限制')
            root = ElementTree.fromstring(archive.read('word/document.xml'))
            text = '\n'.join(''.join(p.itertext()) for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
    elif suffix == '.pdf':
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted or len(reader.pages) > 100:
            raise ValueError('不接受加密PDF或超过100页的PDF')
        text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    else:
        raise ValueError('只支持UTF-8 TXT/Markdown、DOCX和文字PDF；不抓取外部链接')
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text).strip()
    if not text or len(text) > 100_000:
        raise ValueError('提取正文须为1～100000字符；扫描PDF需先自行OCR')
    if re.search(r'eyJ[\w-]+\.[\w-]+\.[\w-]+|\bsk-[A-Za-z0-9_-]{16,}', text):
        raise ValueError('疑似凭证内容，请先移除再上传')
    return text


def index_document(store, ident, version, name, data, embeddings=None):
    try:
        text = extract(name, data)
        # Keep paragraph boundaries where possible, with bounded overlap for long paragraphs.
        parts = []
        for match in re.finditer(r'\S[\s\S]*?(?=\n\s*\n|\Z)', text):
            paragraph = match.group()
            for start in range(0, len(paragraph), 420):
                value = paragraph[start:start+500].strip()
                if value:
                    absolute = match.start() + start + len(paragraph[start:start+500]) - len(paragraph[start:start+500].lstrip())
                    parts.append((value, absolute, text.count('\n', 0, absolute)+1, text.count('\n', 0, absolute+len(value))+1))
        if len(parts) > 250:
            raise ValueError('文档切片超过250段，请拆分文件')
        embedder = embeddings or local_embeddings()
        vectors = embedder.embed_documents([p[0] for p in parts])
        chunks = [dict(text=p[0], offset=p[1], line_start=p[2], line_end=p[3], vector=list(map(float, vector))) for p, vector in zip(parts, vectors)]
        store.document_ready(ident, version, text, chunks)
    except Exception as error:
        message = str(error) if isinstance(error, (ValueError, UnicodeError)) else '解析或本地向量化失败，请检查文件及Embedding依赖'
        store.document_ready(ident, version, error=message)


def search_documents(store, owner, query, *, embeddings=None, limit=3):
    if is_secret_request(query):
        return []
    embedder = embeddings or local_embeddings()
    q = np.asarray(embedder.embed_query(query), dtype=float)
    denominator = np.linalg.norm(q)
    hits = []
    for document in store.documents(owner, vectors=True):
        if document['status'] != 'ready':
            continue
        for number, chunk in enumerate(document['chunks']):
            vector = np.asarray(chunk['vector'], dtype=float)
            score = float(np.dot(vector, q) / max(1e-9, np.linalg.norm(vector) * denominator))
            if score >= .5:
                hits.append(dict(chunk_id=f"{document['id']}-{document['version']}-{number}", text=chunk['text'],
                    source=f"uploaded/{document['id']}", section=document['name'], version=document['sha256'],
                    document_version=document['version'], line_start=chunk.get('line_start',1), line_end=chunk.get('line_end',1),
                    code_references=[], score=round(score, 4)))
    return sorted(hits, key=lambda hit: -hit['score'])[:limit]


def scoped_search(store, owner, base_search):
    def search(query):
        # Caller supplies authenticated owner, never model-selected account IDs.
        if is_secret_request(query):
            return []
        base = base_search(query)
        extra = search_documents(store, owner, query) if any(d['status'] == 'ready' for d in store.documents(owner)) else []
        return sorted(base + extra, key=lambda hit: -hit.get('score', 0))[:3]
    return search
