-- Migración Fase 3

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
