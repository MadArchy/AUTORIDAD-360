import pytest
from unittest.mock import MagicMock
from app.services.argumentative_critic import ArgumentativeCriticService
import json

@pytest.fixture
def mock_db_session():
    return MagicMock()

@pytest.fixture
def critic_service(mock_db_session):
    service = ArgumentativeCriticService(mock_db_session)
    service._complete = MagicMock()
    return service

def test_evaluate_argument_success(critic_service):
    # Setup mock
    mock_response_json = {
        "argumentative_score": 85,
        "critique": "Buen análisis con cita a regulaciones.",
        "suggestions": ["Podría mejorar el hook inicial"]
    }
    critic_service._complete.return_value = (json.dumps(mock_response_json), {})
    
    # Run
    result = critic_service.evaluate_argument(
        draft_text="Borrador de prueba.",
        source_text="Texto original con leyes."
    )
    
    # Assert
    assert result["argumentative_score"] == 85.0
    assert result["critique"] == "Buen análisis con cita a regulaciones."
    assert "Podría mejorar el hook inicial" in result["suggestions"]
    critic_service._complete.assert_called_once()

def test_evaluate_argument_invalid_json(critic_service):
    # Setup mock with invalid JSON
    critic_service._complete.return_value = ("Esto no es un JSON", {})
    
    # Run
    result = critic_service.evaluate_argument(
        draft_text="Borrador de prueba.",
        source_text="Texto original."
    )
    
    # Assert
    assert result["argumentative_score"] == 75.0
    assert "Crítico omitido" in result["critique"] or "Crítico no disponible" in result["critique"]
    
def test_evaluate_argument_gateway_error(critic_service):
    # Setup mock to raise Exception
    critic_service._complete.side_effect = Exception("API Fallida")
    
    # Run
    result = critic_service.evaluate_argument(
        draft_text="Borrador.",
        source_text="Fuente."
    )
    
    # Assert
    assert result["argumentative_score"] == 75.0
    assert "API Fallida" in result["critique"]
