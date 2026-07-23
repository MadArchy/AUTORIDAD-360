from sqlalchemy.orm import Session

from app.models import AuditLog


def log_audit(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    model_used: str | None = None,
    source_url: str | None = None,
    prompt_hash: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
    actor: str | None = None,
    metadata_json: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        model_used=model_used,
        source_url=source_url,
        prompt_hash=prompt_hash,
        input_summary=input_summary,
        output_summary=output_summary,
        actor=actor,
        metadata_json=metadata_json,
    )
    db.add(entry)
    return entry
