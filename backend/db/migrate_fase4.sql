-- Migración Fase 4: calendario, tareas, decisiones, cadencia

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
