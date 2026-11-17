"""Index/parser safety tests use deterministic vectors, not network downloads."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from langchain_core.embeddings import Embeddings

import rag


class FixtureEmbeddings(Embeddings):
    """Token-hash test double; not the production semantic embedding model."""
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        vector = [0.0] * rag.DIMENSION
        for index in range(len(text) - 1):
            key = int(hashlib.sha256(text[index:index + 2].encode()).hexdigest()[:8], 16)
            vector[key % rag.DIMENSION] += 1
        return vector


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="skytwin-rag-test-")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.docs = self.root / "agent/knowledge"
        self.docs.mkdir(parents=True)
        self.file = self.docs / "rules.md"
        self.file.write_text("# 规则\n\n## 禁飞区\n禁飞区禁止飞行，起飞前需要校验。\n\n实现依据：source.java。\n\n## 环境结案\n结案需要处置后证据和完成的侦察任务。\n", encoding="utf-8")
        (self.root / "source.java").write_text("// test fixture", encoding="utf-8")
        self.path = self.root / "index.json"
        self.embeddings = FixtureEmbeddings()
        for name, value in (("KNOWLEDGE_FILES", ("rules.md",)), ("SOURCE_FILES", ("source.java",))):
            patcher = patch.object(rag, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def build(self):
        return rag.build_index(root=self.root, path=self.path, embeddings=self.embeddings)

    def load(self):
        return rag.KnowledgeIndex(root=self.root, path=self.path, embeddings=self.embeddings)

    def test_build_load_and_search_with_traceable_metadata(self):
        self.assertEqual(self.build(), 2)
        results = self.load().search("禁飞区\n禁飞区禁止飞行，起飞前需要校验。")
        self.assertEqual(results[0]["section"], "禁飞区")
        self.assertEqual(results[0]["source"], "agent/knowledge/rules.md")
        self.assertEqual(results[0]["line_start"], 3)
        self.assertIn("source.java", results[0]["code_references"][0])

    def test_no_recursive_ingestion_of_env_or_extra_files(self):
        (self.docs / ".env").write_text("PRIVATE_FIXTURE", encoding="utf-8")
        (self.docs / "unreviewed.md").write_text("UNREVIEWED_FIXTURE", encoding="utf-8")
        self.build()
        self.assertNotIn("PRIVATE_FIXTURE", self.path.read_text(encoding="utf-8"))
        self.assertNotIn("UNREVIEWED_FIXTURE", self.path.read_text(encoding="utf-8"))

    def test_stable_ids_and_overlapping_long_sections(self):
        self.file.write_text("# 标题\n## 长段落\n" + "不同规则文字" * 200, encoding="utf-8")
        first, _ = rag.corpus(self.root)
        second, _ = rag.corpus(self.root)
        self.assertGreater(len(first), 1)
        self.assertEqual([d.id for d in first], [d.id for d in second])
        self.assertTrue(all(len(d.page_content) <= rag.CHUNK_SIZE + 5 for d in first))

    def test_documents_changed_reject_old_index(self):
        self.build()
        self.file.write_text(self.file.read_text(encoding="utf-8") + "新增规则", encoding="utf-8")
        with self.assertRaisesRegex(rag.KnowledgeError, "变化"):
            self.load()

    def test_source_code_changed_rejects_old_index(self):
        self.build()
        (self.root / "source.java").write_text("// changed", encoding="utf-8")
        with self.assertRaisesRegex(rag.KnowledgeError, "变化"):
            self.load()

    def test_running_index_also_rejects_changed_documents(self):
        self.build()
        index = self.load()
        self.file.write_text(self.file.read_text(encoding="utf-8") + "新增规则", encoding="utf-8")
        with self.assertRaisesRegex(rag.KnowledgeError, "变化"):
            index.search("禁飞")

    def test_malformed_index_rejected(self):
        self.path.write_text("invalid-json", encoding="utf-8")
        with self.assertRaisesRegex(rag.KnowledgeError, "损坏"):
            self.load()

    def test_content_and_metadata_tampering_rejected(self):
        for field in ("text", "metadata", "id"):
            self.build()
            data = json.loads(self.path.read_text(encoding="utf-8"))
            record = next(iter(data["store"].values()))
            record[field] = "tampered"
            self.path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(rag.KnowledgeError, "损坏"):
                self.load()

    def test_invalid_vectors_rejected(self):
        for vector in ([0] * 512, [1] * 511, [float("nan")] * 512):
            self.build()
            data = json.loads(self.path.read_text(encoding="utf-8"))
            next(iter(data["store"].values()))["vector"] = vector
            self.path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(rag.KnowledgeError, "损坏"):
                self.load()

    def test_missing_documents_and_index_rejected(self):
        with self.assertRaisesRegex(rag.KnowledgeError, "不存在"):
            self.load()
        self.file.unlink()
        with self.assertRaisesRegex(rag.KnowledgeError, "缺失"):
            rag.corpus(self.root)

    def test_input_bounds_and_zero_relevance(self):
        self.build()
        index = self.load()
        for query in (" ", "x" * 1001):
            with self.assertRaises(rag.KnowledgeError):
                index.search(query)
        with self.assertRaises(rag.KnowledgeError):
            index.search("禁飞", k=4)
        self.assertEqual(index.search("xyzzzzzzzzzzzz"), [])

    def test_model_hash_is_enforced_before_runtime_load(self):
        with patch.object(rag, "MODEL_DIR", self.root):
            (self.root / "model_optimized.onnx").write_bytes(b"not-an-onnx-model")
            with self.assertRaisesRegex(rag.KnowledgeError, "哈希"):
                rag.verify_model()


if __name__ == "__main__":
    unittest.main()
