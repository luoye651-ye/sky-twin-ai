"""Durable AI execution artifacts only. Java remains the business-state authority."""
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid
from contextlib import contextmanager


def encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


class ArtifactConflict(ValueError):
    pass


class ArtifactStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            migration = Path(__file__).resolve().parent.parent / 'ruoyi/backend/sql/agent_artifacts_sqlite_v1.sql'
            db.executescript(migration.read_text(encoding='utf-8'))
            if 'arguments_json' not in {r['name'] for r in db.execute('PRAGMA table_info(ai_span)')}:
                db.executescript(migration.with_name('agent_artifacts_sqlite_v2.sql').read_text(encoding='utf-8'))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=15000')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def recover(self):
        with self.connect() as db:
            db.execute("UPDATE ai_run SET status='interrupted',revision=revision+1,updated=? WHERE status='running'", (time.time(),))
            db.execute("UPDATE ai_span SET status='interrupted',ended=? WHERE status='running'", (time.time(),))
            db.execute("UPDATE ai_document SET status='failed',error='索引被服务重启中断，请重新上传此版本' WHERE status='indexing'")

    def create_run(self, owner, request_id, kind, value, *, daily_limit=30):
        now = time.time()
        payload = encoded(value)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM ai_run WHERE owner=? AND request_id=?', (owner, request_id)).fetchone()
            if old:
                if old['input_json'] != payload or old['kind'] != kind:
                    raise ArtifactConflict('请求编号已用于其他内容')
                return self.decode(old), False
            count = db.execute('SELECT COUNT(*) FROM ai_run WHERE owner=? AND created>?', (owner, now - 86400)).fetchone()[0]
            if count >= daily_limit:
                raise ArtifactConflict('本账号24小时运行额度已用完')
            run_id = 'AR-' + uuid.uuid4().hex
            db.execute('INSERT INTO ai_run(id,owner,request_id,kind,input_json,status,created,updated) VALUES(?,?,?,?,?,?,?,?)',
                       (run_id, owner, request_id, kind, payload, 'pending', now, now))
            return self.decode(db.execute('SELECT * FROM ai_run WHERE id=?', (run_id,)).fetchone()), True

    def existing_request(self, owner, request_id, kind, value):
        with self.connect() as db:
            row = db.execute('SELECT * FROM ai_run WHERE owner=? AND request_id=?', (owner, request_id)).fetchone()
            if row and (row['kind'] != kind or row['input_json'] != encoded(value)):
                raise ArtifactConflict('请求编号已用于其他内容')
            return self.decode(row) if row else None

    @staticmethod
    def decode(row):
        value = dict(row)
        value['input'] = json.loads(value.pop('input_json'))
        value['checkpoint'] = json.loads(value['checkpoint'])
        return value

    def get(self, owner, run_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM ai_run WHERE id=? AND owner=?', (run_id, owner)).fetchone()
            if not row:
                raise KeyError('运行记录不存在')
            value = self.decode(row)
            value['spans'] = [dict(s) for s in db.execute('SELECT * FROM ai_span WHERE run_id=? ORDER BY started,id', (run_id,))]
            for span in value['spans']:
                span['arguments'] = json.loads(span.pop('arguments_json'))
            return value

    def runs(self, owner, page=1):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM ai_run WHERE owner=? ORDER BY created DESC LIMIT 20 OFFSET ?', (owner, (page-1)*20))
            result = [self.decode(r) for r in rows]
            # List never exposes large evidence/checkpoint bodies.
            for row in result:
                row['checkpoint'] = {k: v for k, v in row['checkpoint'].items() if k in ('step', 'message', 'plan_id', 'mode')}
            total = db.execute('SELECT COUNT(*) FROM ai_run WHERE owner=?', (owner,)).fetchone()[0]
            return dict(rows=result, total=total, page=page)

    def claim(self, owner, run_id, revision, allowed):
        with self.connect() as db:
            row = db.execute('SELECT * FROM ai_run WHERE owner=? AND id=?', (owner, run_id)).fetchone()
            if not row:
                raise KeyError('运行记录不存在')
            if row['status'] not in allowed or row['revision'] != revision:
                raise ArtifactConflict('状态或版本已变化，请刷新；运行中的任务不能重复启动')
            changed = db.execute('UPDATE ai_run SET status=?,revision=revision+1,updated=? WHERE id=? AND revision=?',
                                 ('running', time.time(), run_id, revision)).rowcount
            if changed != 1:
                raise ArtifactConflict('运行已被另一个请求处理')
        return self.get(owner, run_id)

    def checkpoint(self, run_id, value, status='running'):
        with self.connect() as db:
            db.execute('UPDATE ai_run SET checkpoint=?,status=?,revision=revision+1,updated=? WHERE id=?',
                       (encoded(value), status, time.time(), run_id))

    def span_start(self, run_id, kind, name, span_id=None, parent=None, arguments=None):
        ident = str(span_id or uuid.uuid4())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if kind == 'model':
                owner = db.execute('SELECT owner FROM ai_run WHERE id=?', (run_id,)).fetchone()[0]
                attempts = db.execute("SELECT COUNT(*) FROM ai_span s JOIN ai_run r ON r.id=s.run_id WHERE r.owner=? AND s.kind='model' AND s.started>?", (owner, time.time()-86400)).fetchone()[0]
                if attempts >= 60:
                    raise ArtifactConflict('本账号24小时最多60次模型调用尝试；请稍后再试')
            db.execute('INSERT OR IGNORE INTO ai_span(id,run_id,parent_id,kind,name,status,started,arguments_json) VALUES(?,?,?,?,?,?,?,?)',
                       (ident, run_id, str(parent) if parent else None, kind, str(name)[:100], 'running', time.time(), encoded(arguments or {})))
        return ident

    def span_end(self, span_id, status='completed', summary='', usage=None):
        usage = usage or {}
        def bounded(key):
            n = usage.get(key)
            return n if type(n) is int and 0 <= n <= 10_000_000 else None
        with self.connect() as db:
            db.execute('UPDATE ai_span SET status=?,ended=?,summary=?,input_tokens=?,output_tokens=? WHERE id=?',
                       (status, time.time(), summary[:500], bounded('input_tokens'), bounded('output_tokens'), str(span_id)))

    def add_document(self, owner, name, data, document_id=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if document_id:
                old = db.execute('SELECT MAX(version) FROM ai_document WHERE id=? AND owner=?', (document_id, owner)).fetchone()[0]
                if old is None:
                    raise KeyError('文档不存在')
                version = old + 1
                db.execute("UPDATE ai_document SET status='superseded' WHERE id=? AND owner=? AND status!='deleted'", (document_id, owner))
            else:
                count = db.execute("SELECT COUNT(DISTINCT id) FROM ai_document WHERE owner=? AND status!='deleted'", (owner,)).fetchone()[0]
                if count >= 20:
                    raise ArtifactConflict('每账号最多20份文档，请先删除旧文档')
                document_id, version = 'KD-' + uuid.uuid4().hex, 1
            db.execute('INSERT INTO ai_document(id,owner,version,name,sha256,status,created) VALUES(?,?,?,?,?,?,?)',
                       (document_id, owner, version, name, hashlib.sha256(data).hexdigest(), 'indexing', time.time()))
        return document_id, version

    def document_ready(self, ident, version, text='', chunks=None, error=''):
        with self.connect() as db:
            db.execute("UPDATE ai_document SET text=?,chunks=?,status=?,error=? WHERE id=? AND version=? AND status='indexing'",
                       (text, encoded(chunks or []), 'failed' if error else 'ready', error[:300], ident, version))

    def documents(self, owner, *, vectors=False):
        with self.connect() as db:
            rows = [dict(r) for r in db.execute('SELECT * FROM ai_document WHERE owner=? ORDER BY created DESC LIMIT 400', (owner,))]
        for row in rows:
            row.pop('text')
            chunks = json.loads(row.pop('chunks'))
            row['chunk_count'] = len(chunks)
            if vectors:
                row['chunks'] = chunks
        return rows

    def delete_document(self, owner, ident):
        with self.connect() as db:
            changed = db.execute("UPDATE ai_document SET status='deleted',text='',chunks='[]' WHERE id=? AND owner=?", (ident, owner)).rowcount
            if not changed:
                raise KeyError('文档不存在')
