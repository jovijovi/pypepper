USE `mock_pypepper`;

CREATE TABLE IF NOT EXISTS `scheduler_jobs` (
  `id` VARCHAR(36) NOT NULL,
  `category` VARCHAR(255) NULL,
  `channel_id` VARCHAR(255) NOT NULL,
  `status` VARCHAR(64) NOT NULL,
  `created` VARCHAR(64) NOT NULL,
  `updated` VARCHAR(64) NOT NULL,
  `workflow_count` INT NOT NULL DEFAULT 0,
  `version` INT NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`),
  KEY `idx_scheduler_jobs_channel_id` (`channel_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
