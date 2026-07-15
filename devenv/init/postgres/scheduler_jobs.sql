CREATE TABLE IF NOT EXISTS scheduler_jobs (
  id VARCHAR(36) PRIMARY KEY,
  category VARCHAR(255),
  channel_id VARCHAR(255) NOT NULL,
  status VARCHAR(64) NOT NULL,
  created VARCHAR(64) NOT NULL,
  updated VARCHAR(64) NOT NULL,
  workflow_count INT NOT NULL DEFAULT 0,
  version INT NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_scheduler_jobs_channel_id ON scheduler_jobs (channel_id);
