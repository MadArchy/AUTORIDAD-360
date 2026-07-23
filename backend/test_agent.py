import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.services.argumentative_critic import ArgumentativeCriticService
import json

# Setup in-memory sqlite DB for testing
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = TestingSessionLocal()

def main():
    print("Iniciando prueba del ArgumentativeCriticService...")
    critic = ArgumentativeCriticService(db)
    
    # Texto fuente ficticio
    source_text = """
    La nueva Ley de Inteligencia Artificial de la UE exige que las empresas de alto riesgo implementen sistemas de gestión de riesgos rigurosos. 
    Las multas pueden llegar hasta el 7% de la facturación global anual. 
    Esto afecta a empresas estadounidenses y mexicanas que ofrecen servicios dentro del mercado europeo.
    Se deben llevar registros detallados de los datos de entrenamiento y asegurar la supervisión humana continua.
    """
    
    # Borrador malo (superficial)
    bad_draft = """
    La inteligencia artificial es revolucionaria. La nueva ley en Europa dice que hay que tener cuidado.
    Las empresas deben prepararse para el futuro porque la tecnología avanza muy rápido.
    ¡Es increíble!
    """
    
    print("\n--- Evaluando Borrador Malo ---")
    try:
        result = critic.evaluate_argument(bad_draft, source_text)
        print("Score:", result.get("argumentative_score"))
        print("Crítica:", result.get("critique"))
        print("Sugerencias:", result.get("suggestions"))
    except Exception as e:
        print("Error evaluando borrador malo:", str(e))
        
    # Borrador bueno (analítico)
    good_draft = """
    La nueva Ley de IA de la UE impone estándares estrictos que trascienden sus fronteras, afectando a empresas en México y EE.UU.
    Al requerir sistemas de gestión de riesgo obligatorios bajo amenaza de multas de hasta el 7% de facturación global, 
    la supervisión humana (human-in-the-loop) deja de ser opcional para convertirse en un mandato de compliance corporativo.
    Las juntas directivas deben auditar inmediatamente sus datasets de entrenamiento.
    """
    
    print("\n--- Evaluando Borrador Bueno ---")
    try:
        result2 = critic.evaluate_argument(good_draft, source_text)
        print("Score:", result2.get("argumentative_score"))
        print("Crítica:", result2.get("critique"))
        print("Sugerencias:", result2.get("suggestions"))
    except Exception as e:
        print("Error evaluando borrador bueno:", str(e))

if __name__ == "__main__":
    main()
