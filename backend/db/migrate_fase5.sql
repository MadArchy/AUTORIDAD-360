-- Migración Fase 5: gateway de modelos + uso

CREATE TABLE IF NOT EXISTS ai_providers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    provider_type VARCHAR(32) NOT NULL,
    model_name VARCHAR(128) NOT NULL,
    base_url VARCHAR(512) NULL,
    encrypted_api_key TEXT NULL,
    key_hint VARCHAR(16) NULL,
    is_local TINYINT(1) NOT NULL DEFAULT 0,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    monthly_budget_usd DECIMAL(10,2) NULL,
    daily_limit_requests INT NULL,
    priority INT NOT NULL DEFAULT 100,
    meta_json JSON NULL,
    last_tested_at DATETIME NULL,
    last_test_ok TINYINT(1) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_provider_active (is_active, priority)
);

CREATE TABLE IF NOT EXISTS ai_usage_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    provider_id BIGINT NULL,
    task_type VARCHAR(64) NOT NULL,
    model_used VARCHAR(128) NOT NULL,
    is_local TINYINT(1) NOT NULL DEFAULT 1,
    success TINYINT(1) NOT NULL DEFAULT 1,
    prompt_tokens INT NULL,
    completion_tokens INT NULL,
    cost_usd DECIMAL(10,6) NULL,
    latency_ms INT NULL,
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usage_created (created_at),
    INDEX idx_usage_provider (provider_id),
    FOREIGN KEY (provider_id) REFERENCES ai_providers(id)
);
