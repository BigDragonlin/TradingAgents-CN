CREATE TABLE IF NOT EXISTS incoming_emails (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  from_email TEXT NOT NULL,
  subject TEXT,
  body TEXT,
  body_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','done','failed')),
  error TEXT,
  claimed_at TEXT,
  worker_id TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(from_email, subject, body_hash)
);

CREATE INDEX IF NOT EXISTS idx_incoming_emails_status_created
  ON incoming_emails(status, created_at);