-- SQLite technical AI artifacts only; not a MySQL/business migration.
CREATE TABLE IF NOT EXISTS ai_run(
              id TEXT PRIMARY KEY,owner INTEGER NOT NULL,request_id TEXT NOT NULL,kind TEXT NOT NULL,
              input_json TEXT NOT NULL,status TEXT NOT NULL,checkpoint TEXT NOT NULL DEFAULT '{}',
              revision INTEGER NOT NULL DEFAULT 1,created REAL NOT NULL,updated REAL NOT NULL,
              UNIQUE(owner,request_id));
            CREATE INDEX IF NOT EXISTS run_owner ON ai_run(owner,created);
            CREATE TABLE IF NOT EXISTS ai_span(
              id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES ai_run(id),parent_id TEXT,
              kind TEXT NOT NULL,name TEXT NOT NULL,status TEXT NOT NULL,started REAL NOT NULL,
              ended REAL,input_tokens INTEGER,output_tokens INTEGER,summary TEXT NOT NULL DEFAULT '',arguments_json TEXT NOT NULL DEFAULT '{}');
            CREATE INDEX IF NOT EXISTS span_run ON ai_span(run_id,started);
            CREATE TABLE IF NOT EXISTS ai_document(
              id TEXT NOT NULL,owner INTEGER NOT NULL,version INTEGER NOT NULL,name TEXT NOT NULL,
              sha256 TEXT NOT NULL,status TEXT NOT NULL,text TEXT NOT NULL DEFAULT '',chunks TEXT NOT NULL DEFAULT '[]',
              error TEXT NOT NULL DEFAULT '',created REAL NOT NULL,PRIMARY KEY(id,version));
