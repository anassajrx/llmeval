import logging
from typing import List, Dict, Any
from sqlalchemy import create_engine, text
from time import sleep
from urllib.parse import quote_plus
import requests

from config.settings import DATABASE_URL, MODEL_CONFIG, RETRY_CONFIG
from core.exceptions import EmbeddingError, DatabaseError
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

class EmbeddingsManager:
    """Gestionnaire des embeddings pour le stockage et la récupération"""
    
    def __init__(self, db_url: str = DATABASE_URL):
        """
        Initialise le gestionnaire d'embeddings avec une connexion à PostgreSQL local
        
        Args:
            db_url (str): URL de connexion à la base de données
        """
        try:
            # Encoder le nom de la base de données s'il contient un espace
            if "Local TestDB" in db_url:
                db_url = db_url.replace("Local TestDB", quote_plus("Local TestDB"))
            
            self.engine = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )
            self.api_key = MODEL_CONFIG['GEMINI_API_KEY']
            self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/embedding-001:embedContent?key={self.api_key}"
            self.setup_database()
            logger.info("EmbeddingsManager initialized successfully with local PostgreSQL")
        except Exception as e:
            error_msg = f"Failed to initialize EmbeddingsManager: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

    def setup_database(self):
        """Configure la base de données PostgreSQL avec pgvector"""
        try:
            with self.engine.connect() as conn:
                # Création de l'extension pgvector
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                
                # Création de la table des embeddings
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        text TEXT NOT NULL,
                        embedding vector(768) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{}'::jsonb
                    )
                """))

                # Index pour la recherche rapide
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
                    ON embeddings 
                    USING ivfflat (embedding vector_cosine_ops)
                """))

                conn.commit()
            logger.info("Database setup completed successfully")
        except Exception as e:
            error_msg = f"Database setup failed: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

    def store_embeddings(self, texts: List[str]) -> None:
            """
            Génère et stocke les embeddings des chunks de texte du PDF
            
            Args:
                texts (List[str]): Liste des chunks de texte du PDF
                
            Raises:
                EmbeddingError: Si une erreur survient lors de la génération/stockage
            """
            headers = {"Content-Type": "application/json"}
            import json
            
            for i, content in enumerate(texts, 1):
                for attempt in range(RETRY_CONFIG['max_retries']):
                    try:
                        logger.info(f"Processing embedding for chunk {i}/{len(texts)} (attempt {attempt + 1})")
                        
                        # Préparation des données pour l'API
                        data = {
                            "model": "embedding-001",
                            "content": {"parts": [{"text": content}]}
                        }

                        # Appel à l'API REST
                        response = requests.post(self.endpoint, headers=headers, json=data)
                        
                        if response.status_code != 200:
                            raise EmbeddingError(f"API error: {response.text}")

                        # Extraction des valeurs d'embedding
                        embedding_response = response.json()
                        embedding_vector = embedding_response["embedding"]["values"]

                        # Création du dictionnaire de métadonnées
                        metadata = {
                            "source": "pdf_chunk",
                            "chunk_number": i,
                            "total_chunks": len(texts),
                            "version": "1.0"
                        }

                        # Stockage dans la base de données avec paramètres nommés
                        with self.engine.connect() as conn:
                            query = text("""
                                INSERT INTO embeddings (text, embedding, metadata) 
                                VALUES (:text, :embedding, :metadata)
                            """)
                            
                            params = {
                                "text": content,
                                "embedding": embedding_vector,
                                "metadata": json.dumps(metadata)
                            }
                            
                            conn.execute(query, params)
                            conn.commit()
                        
                        logger.info(f"Successfully stored embedding for chunk {i}")
                        break
                        
                    except Exception as e:
                        delay = RETRY_CONFIG['base_delay'] * (2 ** attempt)
                        if attempt < RETRY_CONFIG['max_retries'] - 1:
                            logger.warning(f"Attempt {attempt + 1} failed. Retrying in {delay} seconds... Error: {str(e)}")
                            sleep(delay)
                        else:
                            error_msg = f"Failed to store embedding {i} after {RETRY_CONFIG['max_retries']} attempts: {str(e)}"
                            logger.error(error_msg)
                            raise EmbeddingError(error_msg)
                        

    def retrieve_similar_texts(self, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Récupère les textes les plus similaires à un embedding donné
        
        Args:
            query_embedding (List[float]): Embedding de requête
            limit (int): Nombre maximum de résultats
            
        Returns:
            List[Dict[str, Any]]: Liste des textes similaires avec leurs scores
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT 
                            text,
                            metadata,
                            1 - (embedding <=> :query_embedding) as similarity,
                            created_at
                        FROM embeddings
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <=> :query_embedding
                        LIMIT :limit
                    """),
                    {"query_embedding": query_embedding, "limit": limit}
                )
                
                similar_texts = [
                    {
                        "text": row[0],
                        "metadata": row[1],
                        "similarity": float(row[2]),
                        "created_at": row[3]
                    }
                    for row in result
                ]
                
                logger.info(f"Retrieved {len(similar_texts)} similar texts")
                return similar_texts
                
        except Exception as e:
            error_msg = f"Error retrieving similar texts: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

    def clear_embeddings(self) -> None:
        """Supprime tous les embeddings de la base de données"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE embeddings"))
                conn.commit()
            logger.info("Successfully cleared all embeddings")
        except Exception as e:
            error_msg = f"Failed to clear embeddings: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Obtient des statistiques sur les embeddings stockés
        
        Returns:
            Dict[str, Any]: Statistiques sur les embeddings
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_embeddings,
                        MIN(created_at) as oldest_embedding,
                        MAX(created_at) as newest_embedding,
                        pg_size_pretty(pg_total_relation_size('embeddings')) as storage_size
                    FROM embeddings
                """))
                stats = result.fetchone()
                
                return {
                    "total_embeddings": stats[0],
                    "oldest_embedding": stats[1],
                    "newest_embedding": stats[2],
                    "storage_size": stats[3]
                }
                
        except Exception as e:
            error_msg = f"Error getting statistics: {str(e)}"
            logger.error(error_msg)
            raise DatabaseError(error_msg)