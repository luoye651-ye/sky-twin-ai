-- SQLite only, apply once when upgrading an older technical artifact database.
ALTER TABLE ai_span ADD COLUMN arguments_json TEXT NOT NULL DEFAULT '{}';
