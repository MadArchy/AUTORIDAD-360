import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.models import Base, ContentPiece
from app.models.operations import CalendarSlot
from app.services.calendar_ops import advance_slot

# Setup in-memory DB for tests
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_advance_slot_invalid_transition(db_session):
    slot = CalendarSlot(
        status="assigned",
        profile_id=1,
        format_type="linkedin",
        title="Test Slot",
        scheduled_at=datetime.utcnow(),
        risk_level="yellow"
    )
    db_session.add(slot)
    db_session.commit()
    
    with pytest.raises(ValueError, match="Invalid slot transition: assigned → published"):
        advance_slot(db_session, slot, "published", actor="tester")

def test_advance_slot_requires_override_for_red_risk(db_session):
    piece = ContentPiece(
        title="Test",
        package_id=1,
        article_id=1,
        body_text="dummy text",
        source_url="http://test.com",
        format_type="linkedin",
        status="pending_approval",
        factual_review_json={"passed": False, "unsupported_claims": ["claim1", "claim2", "claim3"]} # 3 unsupported triggers red risk
    )
    db_session.add(piece)
    db_session.commit()
    
    slot = CalendarSlot(
        status="pending_approval",
        profile_id=1,
        format_type="linkedin",
        title="Test Slot",
        scheduled_at=datetime.utcnow(),
        piece_id=piece.id
    )
    db_session.add(slot)
    db_session.commit()
    
    with pytest.raises(ValueError, match="Blocked by risk"):
        advance_slot(db_session, slot, "approved", actor="tester", risk_override=False)
        
    # With override and reason, it should pass
    advanced = advance_slot(db_session, slot, "approved", actor="tester", risk_override=True, reason="Checked manually")
    assert advanced.status == "approved"
    assert piece.status == "approved"
