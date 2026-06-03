-- Init script for MySQL Docker container
-- Runs automatically on first container start

CREATE DATABASE IF NOT EXISTS startup_research CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE startup_research;

-- Grant remote access (needed for API and pipeline containers)
CREATE USER IF NOT EXISTS 'app'@'%' IDENTIFIED BY 'startup2024';
GRANT ALL PRIVILEGES ON startup_research.* TO 'app'@'%';
FLUSH PRIVILEGES;
