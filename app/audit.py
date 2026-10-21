from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit(
    db: Session, *, event_type: str, entity_type: str, entity_id: int,
    actor_ref: str, purpose: str, outcome: str, correlation_id: str,
) -> AuditEvent:
    event = AuditEvent(
        event_type=event_type, entity_type=entity_type, entity_id=entity_id,
        actor_ref=actor_ref, purpose=purpose, outcome=outcome,
        correlation_id=correlation_id,
    )
    db.add(event)
    return event
