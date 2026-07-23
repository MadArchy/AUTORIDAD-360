-- Migración Fase 7

CREATE TABLE IF NOT EXISTS leads (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_id BIGINT NULL,
    profile_id BIGINT NOT NULL,
    pillar_id BIGINT NULL,
    piece_id BIGINT NULL,
    source_channel VARCHAR(64) NOT NULL DEFAULT 'linkedin',
    contact_name VARCHAR(256) NOT NULL,
    contact_email VARCHAR(256) NULL,
    contact_company VARCHAR(256) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'new',
    is_qualified TINYINT(1) NOT NULL DEFAULT 0,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    converted_at DATETIME NULL,
    INDEX idx_leads_profile (profile_id),
    INDEX idx_leads_status (status),
    INDEX idx_leads_pillar (pillar_id)
);

CREATE TABLE IF NOT EXISTS content_engagements (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_id BIGINT NULL,
    profile_id BIGINT NOT NULL,
    piece_id BIGINT NULL,
    pillar_id BIGINT NULL,
    likes INT NOT NULL DEFAULT 0,
    comments INT NOT NULL DEFAULT 0,
    shares INT NOT NULL DEFAULT 0,
    impressions INT NOT NULL DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS percentage_recommendations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_id BIGINT NULL,
    profile_id BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    rationale TEXT NOT NULL,
    evidence_json JSON NOT NULL,
    changes_json JSON NOT NULL,
    min_qualified_leads INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decided_at DATETIME NULL,
    decided_by VARCHAR(128) NULL,
    decision_reason TEXT NULL
);

CREATE TABLE IF NOT EXISTS metric_snapshots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_id BIGINT NULL,
    profile_id BIGINT NULL,
    period_days INT NOT NULL DEFAULT 30,
    metrics_json JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
