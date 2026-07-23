import os
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Intento de importar dependencias pesadas
HAS_CHROMADB = False
try:
    import chromadb
    from chromadb import Documents, EmbeddingFunction, Embeddings
    from litellm import embedding
    HAS_CHROMADB = True
except ImportError as e:
    logger.warning(
        "ChromaDB no instalado (%s). Motor vectorial en modo dummy (piloto OK).",
        e,
    )

if HAS_CHROMADB:
    class LiteLLMEmbeddingFunction(EmbeddingFunction):
        def __init__(self, model_name: str | None = None, api_base: str | None = None):
            self.model_name = model_name or settings.vector_embedding_model
            self.api_base = api_base or settings.ollama_base_url
            
        def __call__(self, input: Documents) -> Embeddings:
            if not input:
                return []
            try:
                response = embedding(
                    model=self.model_name,
                    input=input,
                    api_base=self.api_base if self.model_name.startswith("ollama/") else None
                )
                return [item["embedding"] for item in response.data]
            except Exception as e:
                logger.error(f"Error generando embeddings: {e}")
                # Nunca devolver vector cero (Etapa 2) — falla la operación
                raise RuntimeError(f"embedding_failed: {e}") from e


class VectorEngineService:
    def __init__(self):
        self.is_active = HAS_CHROMADB
        if not self.is_active:
            return
            
        self.persist_directory = os.path.join(os.getcwd(), "chroma_data")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.embedding_fn = LiteLLMEmbeddingFunction(
                model_name=getattr(settings, "vector_embedding_model", "ollama/nomic-embed-text"),
                api_base=getattr(settings, "ollama_base_url", "http://localhost:11434")
            )
            self.collection = self.client.get_or_create_collection(
                name="articles_collection",
                embedding_function=self.embedding_fn
            )
            logger.info(f"VectorEngine inicializado en {self.persist_directory}")
        except Exception as e:
            logger.error(f"Fallo al inicializar ChromaDB: {e}")
            self.is_active = False

    def index_article(self, article_id: int, title: str, content: str, category: str = "editorial") -> bool:
        """Indexa artículo. False = embedding_status debería marcarse failed en el caller."""
        if not self.is_active:
            return False
        try:
            doc_text = f"Title: {title}\nContent: {content}"
            self.collection.upsert(
                documents=[doc_text],
                metadatas=[{"title": title, "category": category, "embedding_status": "ok"}],
                ids=[f"art_{article_id}"]
            )
            return True
        except Exception as e:
            logger.error(f"Error indexando en VectorEngine (embedding_status=failed): {e}")
            return False

    def search_similar(self, query: str, n_results: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.is_active: return []
        try:
            where_clause = {"category": category} if category else None
            results = self.collection.query(query_texts=[query], n_results=n_results, where=where_clause)
            
            formatted_results = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                for idx, doc_id in enumerate(results["ids"][0]):
                    formatted_results.append({
                        "id": doc_id,
                        "distance": results["distances"][0][idx] if "distances" in results and results["distances"] else 0.0,
                        "metadata": results["metadatas"][0][idx] if "metadatas" in results and results["metadatas"] else {},
                        "document": results["documents"][0][idx] if "documents" in results and results["documents"] else ""
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"Error buscando en VectorEngine: {e}")
            return []

    def check_is_duplicate(self, content: str, threshold: float = 0.2) -> bool:
        if not self.is_active: return False
        try:
            results = self.collection.query(query_texts=[content], n_results=1)
            if results and results.get("distances") and len(results["distances"][0]) > 0:
                return results["distances"][0][0] < threshold
            return False
        except Exception:
            return False

vector_engine = VectorEngineService()
