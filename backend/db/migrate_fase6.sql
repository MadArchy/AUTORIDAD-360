-- Migración Fase 6: multiempresa

CREATE TABLE IF NOT EXISTS organizations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(256) NOT NULL,
    org_type VARCHAR(32) NOT NULL DEFAULT 'agency',
    parent_id BIGINT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES organizations(id)
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
    UNIQUE KEY uq_org_user (organization_id, user_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES app_users(id),
    FOREIGN KEY (profile_id) REFERENCES professional_profiles(id)
);

-- Añadir organization_id a tablas operativas (ignorar error si ya existe)
ALTER TABLE news_categories ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE news_articles ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE weekly_reports ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE blog_posts ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE audit_logs ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE professional_profiles ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE content_packages ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE content_pieces ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE cadence_rules ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE calendar_slots ADD COLUMN organization_id BIGINT NULL;
ALTER TABLE ai_providers ADD COLUMN organization_id BIGINT NULL;
