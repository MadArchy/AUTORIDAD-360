from sqlalchemy import text
from app.db.database import engine

def migrate_schema():
    with engine.connect() as conn:
        # Check existing columns in news_articles
        res = conn.execute(text("PRAGMA table_info(news_articles)"))
        existing_cols = {row[1] for row in res.fetchall()}
        
        if "verification_reason" not in existing_cols:
            print("Agregando columna 'verification_reason' a news_articles...")
            conn.execute(text("ALTER TABLE news_articles ADD COLUMN verification_reason TEXT"))
            
        if "verified_at" not in existing_cols:
            print("Agregando columna 'verified_at' a news_articles...")
            conn.execute(text("ALTER TABLE news_articles ADD COLUMN verified_at DATETIME"))
            
        conn.commit()
        print("Migración de esquema completada exitosamente.")

if __name__ == "__main__":
    migrate_schema()
