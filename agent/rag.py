"""Local Chinese vector RAG for reviewed project rules; uploaded knowledge is owner-scoped separately."""
from functools import lru_cache
import hashlib
import json
import re
from pathlib import Path
import uuid
from safety_policy import is_secret_request

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

AGENT_DIR = Path(__file__).resolve().parent
ROOT = AGENT_DIR.parent
KNOWLEDGE_FILES = ("platform.md", "airspace.md", "response.md", "operations.md")
JAVA_DIR = "ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/"
SOURCE_FILES = tuple(JAVA_DIR + name for name in (
    "SkyController.java", "SkyService.java", "AirspaceService.java", "AirspaceEngine.java",
    "EnvironmentService.java", "EnvironmentRules.java", "PatrolEvaluationService.java",
    "DispatchController.java", "DispatchService.java", "VisionAnalysisService.java",
    "TaskOperationsService.java", "ResourceOperationsService.java", "OperationsRules.java", "CommuteService.java",
    "OperationsReportService.java", "OperationsController.java", "DetourPlanner.java", "RouteService.java",
)) + ("ruoyi/backend/sql/sky_twin_v8_environment.sql", "agent/aircraft_agent.py", "agent/mcp_server.py", "agent/dispatch_tools.py", "agent/conversation_store.py", "ai/scripts/vision_upload.py",
      "agent/workbench_api.py", "agent/workbench_service.py", "agent/workbench_store.py", "agent/workbench_knowledge.py", "agent/workbench_trace.py", "agent/safety_policy.py", "agent/vision_chat.py", "ruoyi/backend/sql/agent_artifacts_sqlite_v1.sql")
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
MODEL_REPO = "Qdrant/bge-small-zh-v1.5"
MODEL_REVISION = "46fbe35fd4374a00fee7de77dfddaeb6dd6a2c59"
MODEL_SHA256 = "1294ea4b6331115a353d81f96b85e8c8d7fdcc284453d5b2fab5b016230aad38"
MODEL_DIR = AGENT_DIR / ".cache/models/bge-small-zh-v1.5"
INDEX_PATH = AGENT_DIR / ".cache/knowledge-index.json"
DIMENSION = 512
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
CHUNK_SIZE, CHUNK_OVERLAP = 380, 50
MIN_SCORE = 0.50  # Calibrated on the small regression set, not a probability or accuracy claim.


class KnowledgeError(RuntimeError):
    """Safe local setup/index error."""


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare_model() -> None:
    """Explicit one-time public model download, no platform/provider credentials."""
    from huggingface_hub import snapshot_download
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=MODEL_REPO, revision=MODEL_REVISION, token=False,
        local_dir=str(MODEL_DIR), max_workers=2,
        allow_patterns=["model_optimized.onnx", "config.json", "ort_config.json", "tokenizer.json",
                        "tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "README.md"],
    )
    verify_model()


def verify_model() -> None:
    model = MODEL_DIR / "model_optimized.onnx"
    if not model.is_file() or sha256(model) != MODEL_SHA256:
        raise KnowledgeError("本地Embedding模型缺失或哈希不符，请运行 rag_cli.py prepare。")


class LocalChineseEmbeddings(Embeddings):
    def __init__(self):
        verify_model()
        from fastembed import TextEmbedding
        self.model = TextEmbedding(
            model_name=MODEL_NAME, specific_model_path=str(MODEL_DIR),
            local_files_only=True, threads=2, providers=["CPUExecutionProvider"],
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.model.passage_embed(texts, batch_size=16)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self.model.query_embed(QUERY_PREFIX + text))).tolist()


@lru_cache(maxsize=1)
def local_embeddings() -> LocalChineseEmbeddings:
    return LocalChineseEmbeddings()


def corpus(root: Path = ROOT) -> tuple[list[Document], dict]:
    """Never recursively scan the repo, .env, logs, datasets or business exports."""
    documents, hashes = [], {}
    folder = (root / "agent/knowledge").resolve()
    for name in KNOWLEDGE_FILES:
        path = folder / name
        if path.resolve().parent != folder or not path.is_file() or path.stat().st_size > 100_000:
            raise KnowledgeError("知识文档缺失、路径越界或过大，请核对agent/knowledge。")
        hashes[f"agent/knowledge/{name}"] = sha256(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        headings = [(i, line[3:].strip()) for i, line in enumerate(lines) if line.startswith("## ")]
        for number, (start, section) in enumerate(headings):
            end = headings[number + 1][0] if number + 1 < len(headings) else len(lines)
            body = "\n".join(line for line in lines[start + 1:end] if not line.startswith("实现依据：")).strip()
            references = [line.removeprefix("实现依据：") for line in lines[start + 1:end] if line.startswith("实现依据：")]
            for offset in range(0, len(body), CHUNK_SIZE - CHUNK_OVERLAP):
                text = body[offset:offset + CHUNK_SIZE]
                if not text:
                    continue
                ident = hashlib.sha256(f"{name}:{section}:{offset}:{text}".encode()).hexdigest()[:16]
                documents.append(Document(id=ident, page_content=f"{section}\n{text}", metadata={
                    "version": hashes[f"agent/knowledge/{name}"], "chunk_id": ident, "source": f"agent/knowledge/{name}", "section": section,
                    "line_start": start + 1, "line_end": end, "code_references": references,
                }))
                if offset + CHUNK_SIZE >= len(body):
                    break
    if not documents:
        raise KnowledgeError("知识文档没有可索引的二级章节。")
    try:
        source_hashes = {name: sha256(root / name) for name in SOURCE_FILES}
    except OSError:
        raise KnowledgeError("知识依据代码缺失，无法检查文档新鲜度。") from None
    manifest = {
        "version": 1, "model": MODEL_NAME, "revision": MODEL_REVISION, "model_sha256": MODEL_SHA256,
        "dimension": DIMENSION, "query_prefix": QUERY_PREFIX, "retrieval": "semantic-gated-rrf-v1",
        "chunk_size": CHUNK_SIZE, "overlap": CHUNK_OVERLAP,
        "documents": hashes, "code": source_hashes,
    }
    return documents, manifest


def build_index(*, root: Path = ROOT, path: Path = INDEX_PATH, embeddings: Embeddings | None = None) -> int:
    docs, manifest = corpus(root)
    store = InMemoryVectorStore(embeddings if embeddings is not None else local_embeddings())
    store.add_documents(docs)
    payload = {"manifest": manifest, "store": store.store}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return len(docs)


class KnowledgeIndex:
    def __init__(self, *, root: Path = ROOT, path: Path = INDEX_PATH, embeddings: Embeddings | None = None):
        self.root, self.path = root, path
        self.docs, self.manifest = corpus(root)
        if not path.is_file():
            raise KnowledgeError("知识索引不存在，请运行 rag_cli.py build。")
        try:
            if path.stat().st_size > 5_000_000:
                raise ValueError("oversize")
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload["manifest"] != self.manifest:
                raise KnowledgeError("知识文档或依据代码已变化，请核对文档后运行 rag_cli.py build 重建。")
            records = payload["store"]
            if set(records) != {doc.id for doc in self.docs}:
                raise ValueError("ids")
            for doc in self.docs:
                item = records[doc.id]
                vector = np.asarray(item["vector"], dtype=float)
                if item["id"] != doc.id or item["text"] != doc.page_content or item["metadata"] != doc.metadata:
                    raise ValueError("content")
                if vector.shape != (DIMENSION,) or not np.isfinite(vector).all() or np.linalg.norm(vector) < 1e-9:
                    raise ValueError("vector")
        except KnowledgeError:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            raise KnowledgeError("知识索引损坏或格式异常，请运行 rag_cli.py build 重建。") from None
        self.store = InMemoryVectorStore(embeddings if embeddings is not None else local_embeddings())
        self.store.store = records

    def search(self, query: str, *, k: int = 3) -> list[dict]:
        query = query.strip()
        if not query or len(query) > 1000 or k not in (1, 2, 3):
            raise KnowledgeError("知识检索问题须为1～1000字符，最多返回3段。")
        if is_secret_request(query):
            return []
        # A running process must not silently keep stale code/document snapshots.
        if corpus(self.root)[1] != self.manifest:
            raise KnowledgeError("知识文档或依据代码已变化，请核对后重建索引。")
        results = self.store.similarity_search_with_score(query, k=len(self.docs))
        eligible = [(doc, float(score)) for doc, score in results if score >= MIN_SCORE]
        # Lexical ranking complements semantic retrieval only inside its relevance gate.
        def terms(text):
            text = text.lower()
            chinese = re.findall(r"[\u4e00-\u9fff]+", text)
            return set(re.findall(r"[a-z0-9_]+", text)) | {part[i:i+2] for part in chinese for i in range(len(part)-1)}
        query_terms = terms(query)
        lexical = sorted(eligible, key=lambda item: (-len(query_terms & terms(item[0].page_content)), item[0].id))
        lexical_rank = {doc.id: rank for rank, (doc, _score) in enumerate(lexical, 1)}
        ranked = [(doc, score, 1/(60+rank) + 1/(60+lexical_rank[doc.id]))
                  for rank, (doc, score) in enumerate(eligible, 1)]
        ranked.sort(key=lambda item: (-item[2], -item[1], item[0].id))
        return [dict(doc.metadata, text=doc.page_content, score=round(score, 4), retrieval="semantic-gated-rrf-v1")
                for doc, score, _rank in ranked[:k]]


@lru_cache(maxsize=1)
def get_index() -> KnowledgeIndex:
    return KnowledgeIndex()


def search_knowledge(query: str) -> list[dict]:
    return get_index().search(query)
