import json
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.profile import ProfessionalProfile, ContentPillar, MarketPercentage
from app.models.news import NewsArticle
from app.schemas.profile import ProfileResponse, PillarSchema, MarketPctSchema

logger = logging.getLogger(__name__)

DEFAULT_JUAN_PROFILE = {
    "full_name": "Juan Vásquez",
    "title": "Consultor en Inteligencia Artificial & Abogado Estratega Tech",
    "bio": "Especialista en estructuración legal, gobernanza de datos y adopción ética y regulada de IA para empresas en México y Estados Unidos.",
    "target_audiences": ["CEOs & Fundadores Tech", "Directores Jurídicos / General Counsel", "VP de Innovación y CTOs", "Inversionistas VC"],
    "services": [
        "Consultoría en Gobernanza y Cumplimiento de IA",
        "Estrategia Legal y Propiedad Intelectual Tech",
        "Mitigación de Riesgos de Ciberseguridad y Datos",
        "Asesoría en Expansión y Regulación Cross-Border (MX-US)"
    ],
    "pillars": [
        {"name": "Inteligencia Artificial & Transformación", "category_key": "ia_y_transformacion_digital", "target_percentage": 35.0, "description": "Modelos, agentes, automatización y tendencias de IA."},
        {"name": "Derecho Tech & Regulación Cross-Border", "category_key": "derecho_y_regulacion_tech", "target_percentage": 25.0, "description": "Leyes de IA, privacidad, regulaciones MX-US y USMCA."},
        {"name": "Ciberseguridad & Gobernanza de Datos", "category_key": "ciberseguridad_y_privacidad", "target_percentage": 20.0, "description": "Protección de datos, incidentes de seguridad y cumplimiento."},
        {"name": "Estrategia Empresarial & Propiedad Intelectual", "category_key": "propiedad_intelectual_y_datos", "target_percentage": 20.0, "description": "Marcas, patentes, estrategia legal de negocios y fintech."}
    ],
    "markets": [
        {"market_code": "MX", "market_name": "México", "target_percentage": 60.0},
        {"market_code": "US", "market_name": "Estados Unidos / Internacional", "target_percentage": 40.0}
    ]
}

class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_profile(self) -> ProfessionalProfile:
        """Retrieves or initializes Juan Vásquez's default profile and editorial targets."""
        profile = self.db.query(ProfessionalProfile).first()
        if not profile:
            profile = ProfessionalProfile(
                full_name=DEFAULT_JUAN_PROFILE["full_name"],
                title=DEFAULT_JUAN_PROFILE["title"],
                bio=DEFAULT_JUAN_PROFILE["bio"],
                target_audiences=json.dumps(DEFAULT_JUAN_PROFILE["target_audiences"], ensure_ascii=False),
                services=json.dumps(DEFAULT_JUAN_PROFILE["services"], ensure_ascii=False)
            )
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)

            # Create default pillars
            for p in DEFAULT_JUAN_PROFILE["pillars"]:
                pillar = ContentPillar(
                    profile_id=profile.id,
                    name=p["name"],
                    category_key=p["category_key"],
                    target_percentage=p["target_percentage"],
                    description=p["description"]
                )
                self.db.add(pillar)

            # Create default markets
            for m in DEFAULT_JUAN_PROFILE["markets"]:
                market = MarketPercentage(
                    profile_id=profile.id,
                    market_code=m["market_code"],
                    market_name=m["market_name"],
                    target_percentage=m["target_percentage"]
                )
                self.db.add(market)

            self.db.commit()
            self.db.refresh(profile)

        return profile

    def get_profile_with_quota_stats(self) -> Dict[str, Any]:
        """Calculates current month coverage vs target percentage for quota correction."""
        profile = self.get_or_create_profile()
        
        # Count total articles in DB for percentage calculation
        total_articles = self.db.query(NewsArticle).count() or 1

        pillar_schemas = []
        quota_boosts = {} # category_key -> multiplier boost

        for p in profile.pillars:
            count = self.db.query(NewsArticle).filter(NewsArticle.category == p.category_key).count()
            current_pct = round((count / total_articles) * 100.0, 1)

            # Quota deficit check
            deficit = p.target_percentage - current_pct
            if deficit > 5.0:
                quota_status = "below_quota"
                # Dynamic boost for Top 10 scoring engine (e.g., +25% to +50% priority boost)
                boost = 1.0 + min(deficit / 100.0, 0.5)
            elif current_pct > p.target_percentage + 10.0:
                quota_status = "above_quota"
                boost = 0.85 # Slight priority dampening for overrepresented topics
            else:
                quota_status = "balanced"
                boost = 1.0

            quota_boosts[p.category_key] = boost

            pillar_schemas.append({
                "id": p.id,
                "name": p.name,
                "category_key": p.category_key,
                "target_percentage": p.target_percentage,
                "description": p.description,
                "current_month_count": count,
                "current_month_pct": current_pct,
                "quota_status": quota_status,
                "quota_boost": round(boost, 2)
            })

        markets_schemas = []
        for m in profile.markets:
            markets_schemas.append({
                "id": m.id,
                "market_code": m.market_code,
                "market_name": m.market_name,
                "target_percentage": m.target_percentage
            })

        audiences = []
        services = []
        try:
            audiences = json.loads(profile.target_audiences or "[]")
            services = json.loads(profile.services or "[]")
        except Exception:
            pass

        return {
            "id": profile.id,
            "full_name": profile.full_name,
            "title": profile.title,
            "bio": profile.bio,
            "target_audiences": audiences,
            "services": services,
            "pillars": pillar_schemas,
            "markets": markets_schemas,
            "quota_boosts": quota_boosts,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
        }
