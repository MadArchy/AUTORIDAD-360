"""Migración Fase 2 — ejecutar si MySQL ya existía antes de estas tablas.

  docker exec -i autoridad360-mysql mysql -uautoridad -pautoridadpass autoridad360 < backend/db/migrate_fase2.sql
"""

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
