-- Autoridad 360 — Fase 1 schema

CREATE TABLE IF NOT EXISTS news_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    rss_url VARCHAR(512) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_articles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    title VARCHAR(512) NOT NULL,
    source_url VARCHAR(1024) NOT NULL,
    source_name VARCHAR(256) NOT NULL,
    published_at DATETIME NULL,
    full_text MEDIUMTEXT NOT NULL,
    excerpt TEXT NULL,
    content_hash CHAR(64) NOT NULL,
    status ENUM('collected','classified','verified','rejected','approved','published') NOT NULL DEFAULT 'collected',
    classification_json JSON NULL,
    verification_json JSON NULL,
    score_relevance DECIMAL(5,2) NULL,
    score_impact DECIMAL(5,2) NULL,
    score_reliability DECIMAL(5,2) NULL,
    score_freshness DECIMAL(5,2) NULL,
    score_content_potential DECIMAL(5,2) NULL,
    score_mx_us_relevance DECIMAL(5,2) NULL,
    score_conversion DECIMAL(5,2) NULL,
    total_score DECIMAL(6,2) NULL,
    summary TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_content_hash (content_hash),
    UNIQUE KEY uq_source_url (source_url(768)),
    INDEX idx_status_score (status, total_score DESC),
    INDEX idx_published_at (published_at),
    FOREIGN KEY (category_id) REFERENCES news_categories(id)
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    report_json JSON NOT NULL,
    markdown_content MEDIUMTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_week (week_start, week_end)
);

CREATE TABLE IF NOT EXISTS blog_posts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    article_id BIGINT NOT NULL,
    title VARCHAR(512) NOT NULL,
    slug VARCHAR(512) NOT NULL UNIQUE,
    content_html MEDIUMTEXT NOT NULL,
    source_url VARCHAR(1024) NOT NULL,
    source_citation TEXT NOT NULL,
    status ENUM('pending','approved','rejected','published') NOT NULL DEFAULT 'pending',
    approved_by VARCHAR(128) NULL,
    approved_at DATETIME NULL,
    rejection_reason TEXT NULL,
    published_at DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES news_articles(id),
    INDEX idx_blog_status (status)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,
    entity_id BIGINT NOT NULL,
    action VARCHAR(64) NOT NULL,
    model_used VARCHAR(128) NULL,
    source_url VARCHAR(1024) NULL,
    prompt_hash CHAR(64) NULL,
    input_summary TEXT NULL,
    output_summary TEXT NULL,
    actor VARCHAR(128) NULL,
    metadata_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_created (created_at)
);

-- Fase 2: perfil estratégico y porcentajes editoriales

CREATE TABLE IF NOT EXISTS professional_profiles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    full_name VARCHAR(256) NOT NULL,
    title VARCHAR(256) NULL,
    bio TEXT NULL,
    services_json JSON NULL,
    audiences_json JSON NULL,
    markets_json JSON NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_pillars (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    profile_id BIGINT NOT NULL,
    slug VARCHAR(64) NOT NULL,
    name VARCHAR(128) NOT NULL,
    description TEXT NULL,
    keywords_json JSON NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_profile_pillar (profile_id, slug),
    FOREIGN KEY (profile_id) REFERENCES professional_profiles(id)
);

CREATE TABLE IF NOT EXISTS editorial_percentages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    profile_id BIGINT NOT NULL,
    pillar_id BIGINT NOT NULL,
    target_pct DECIMAL(5,2) NOT NULL,
    period VARCHAR(16) NOT NULL DEFAULT 'monthly',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_profile_pillar_pct (profile_id, pillar_id, period),
    FOREIGN KEY (profile_id) REFERENCES professional_profiles(id),
    FOREIGN KEY (pillar_id) REFERENCES content_pillars(id)
);

CREATE TABLE IF NOT EXISTS market_percentages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    profile_id BIGINT NOT NULL,
    market_code VARCHAR(8) NOT NULL,
    target_pct DECIMAL(5,2) NOT NULL,
    period VARCHAR(16) NOT NULL DEFAULT 'monthly',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_profile_market (profile_id, market_code, period),
    FOREIGN KEY (profile_id) REFERENCES professional_profiles(id)
);

-- Fase 3: contenido multi-formato

CREATE TABLE IF NOT EXISTS content_packages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    article_id BIGINT NOT NULL,
    profile_id BIGINT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES news_articles(id),
    FOREIGN KEY (profile_id) REFERENCES professional_profiles(id),
    INDEX idx_pkg_article (article_id),
    INDEX idx_pkg_status (status)
);

CREATE TABLE IF NOT EXISTS content_pieces (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    package_id BIGINT NOT NULL,
    article_id BIGINT NOT NULL,
    parent_piece_id BIGINT NULL,
    format_type VARCHAR(32) NOT NULL,
    language VARCHAR(8) NOT NULL DEFAULT 'es',
    title VARCHAR(512) NOT NULL,
    body_text MEDIUMTEXT NOT NULL,
    body_json JSON NULL,
    source_url VARCHAR(1024) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    version INT NOT NULL DEFAULT 1,
    factual_review_json JSON NULL,
    brand_review_json JSON NULL,
    generation_json JSON NULL,
    approved_by VARCHAR(128) NULL,
    approved_at DATETIME NULL,
    rejection_reason TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (package_id) REFERENCES content_packages(id),
    FOREIGN KEY (article_id) REFERENCES news_articles(id),
    FOREIGN KEY (parent_piece_id) REFERENCES content_pieces(id),
    INDEX idx_piece_status (status),
    INDEX idx_piece_format (format_type),
    INDEX idx_piece_article (article_id)
);

-- Fase 4: calendario, tareas, decisiones

CREATE TABLE IF NOT EXISTS cadence_rules (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    profile_id BIGINT NOT NULL,
    format_type VARCHAR(32) NOT NULL,
    frequency VARCHAR(16) NOT NULL,
    target_count INT NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_cadence (profile_id, format_type, frequency),
    FOREIGN KEY (profile_id) REFERENCES professional_profiles(id)
);

CREATE TABLE IF NOT EXISTS calendar_slots (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    profile_id BIGINT NOT NULL,
    piece_id BIGINT NULL,
    format_type VARCHAR(32) NOT NULL,
    title VARCHAR(512) NOT NULL,
    scheduled_at DATETIME NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'planned',
    risk_level VARCHAR(16) NOT NULL DEFAULT 'yellow',
    risk_json JSON NULL,
    channel VARCHAR(64) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_slot_scheduled (scheduled_at),
    INDEX idx_slot_status (status),
    FOREIGN KEY (profile_id) REFERENCES professional_profiles(id),
    FOREIGN KEY (piece_id) REFERENCES content_pieces(id)
);

CREATE TABLE IF NOT EXISTS editorial_tasks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    slot_id BIGINT NOT NULL,
    piece_id BIGINT NULL,
    task_type VARCHAR(32) NOT NULL,
    title VARCHAR(256) NOT NULL,
    assignee VARCHAR(128) NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'todo',
    due_at DATETIME NULL,
    attachment_url VARCHAR(1024) NULL,
    attachment_notes TEXT NULL,
    completed_at DATETIME NULL,
    completed_by VARCHAR(128) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_task_status (status),
    FOREIGN KEY (slot_id) REFERENCES calendar_slots(id),
    FOREIGN KEY (piece_id) REFERENCES content_pieces(id)
);

CREATE TABLE IF NOT EXISTS decision_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,
    entity_id BIGINT NOT NULL,
    action VARCHAR(64) NOT NULL,
    from_status VARCHAR(32) NULL,
    to_status VARCHAR(32) NULL,
    risk_level VARCHAR(16) NULL,
    actor VARCHAR(128) NOT NULL,
    reason TEXT NULL,
    version INT NULL,
    snapshot_json JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_decision_entity (entity_type, entity_id),
    INDEX idx_decision_created (created_at)
);

-- Fase 5: gateway AI

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

-- Fase 6: multiempresa
CREATE TABLE IF NOT EXISTS organizations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(256) NOT NULL,
    org_type VARCHAR(32) NOT NULL DEFAULT 'agency',
    parent_id BIGINT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS app_users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(256) NOT NULL UNIQUE,
    full_name VARCHAR(256) NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    is_superadmin TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS org_memberships (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role VARCHAR(32) NOT NULL,
    profile_id BIGINT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_org_user (organization_id, user_id)
);
