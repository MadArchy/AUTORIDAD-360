import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.models.ai_providers import AIProvider

db = SessionLocal()
anthropic = db.query(AIProvider).filter(AIProvider.provider_type == "anthropic").first()
if anthropic and anthropic.model_name == "claude-3-5-sonnet":
    anthropic.model_name = "anthropic/claude-3-5-sonnet-20240620"
    db.commit()
    print("Updated Anthropic model name in database.")
else:
    print("No update needed for Anthropic model name.")

print("Update script finished.")
