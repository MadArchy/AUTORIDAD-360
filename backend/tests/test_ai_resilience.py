import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.ai_providers import AIProvider
from app.services.ai_gateway import AIGatewayService

engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Seed default providers
    service = AIGatewayService(db)
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

@patch("app.services.ai_gateway.AIGatewayService._call_ollama")
@patch("app.services.ai_gateway.AIGatewayService._call_cloud_provider")
def test_ai_gateway_strict_failure(mock_cloud, mock_ollama, db_session):
    # Setup mocks to always fail
    mock_ollama.side_effect = Exception("Ollama is down")
    mock_cloud.side_effect = Exception("API limit exceeded")
    
    service = AIGatewayService(db_session)
    
    with pytest.raises(RuntimeError, match="All AI providers failed"):
        service.generate_text("Test prompt")
        
    # Verify both methods were attempted (fallback chain)
    assert mock_ollama.called
    assert mock_cloud.called
