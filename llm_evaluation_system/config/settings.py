from pathlib import Path
import logging
import google.generativeai as genai
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_api_key(file_path: str) -> str:
    """Load API key from .env.apikey file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read().strip()
            return content.split('=')[1].strip().strip('"')
    except Exception as e:
        logger.error(f"Error loading API key from {file_path}: {str(e)}")
        raise

# Configuration des chemins
WORKSPACE_DIR = Path(__file__).parent.parent.parent
GEMINI_API_KEY_PATH = WORKSPACE_DIR / "AI_API/API_Calls/GeminiProAPI/settings/.env.apikey"
DATABASE_URL_PATH = WORKSPACE_DIR / "AI_API/API_Calls/PostgresURL/settings/.env.apikey"

# Chargement des clés API
try:
    GEMINI_API_KEY = load_api_key(GEMINI_API_KEY_PATH)
    DATABASE_URL = load_api_key(DATABASE_URL_PATH)
except Exception as e:
    logger.critical(f"Failed to load API keys: {str(e)}")
    raise

# Configuration de l'API Gemini avec transport=rest
# Configuration de l'API Gemini avec transport=rest pour toutes les opérations
genai.configure(
    api_key=GEMINI_API_KEY,
    transport='rest',
)


# Configuration des chemins
WORKSPACE_DIR = Path(__file__).parent.parent  # Pointe vers llm_evaluation_system
DATA_DIR = WORKSPACE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

# Debug des chemins
logger.info(f"WORKSPACE_DIR: {WORKSPACE_DIR}")
logger.info(f"DATA_DIR: {DATA_DIR}")
logger.info(f"INPUT_DIR: {INPUT_DIR}")

# S'assurer que les répertoires existent
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"Input directory path: {INPUT_DIR}")

# Configuration du modèle avec transport explicite
MODEL_CONFIG = {
    "embedding_model": "models/embedding-001",
    "generation_model": "gemini-2.0-flash",
    "temperature": 0,
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "transport": "rest",  # Configuration explicite du transport
}
# Configuration des chunks pour le traitement des documents
CHUNK_CONFIG = {
    "chunk_size": 1000,
    "chunk_overlap": 200
}

# Configuration des délais et tentatives
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 20,
    "max_delay": 60
}

# Configuration de l'évaluation
EVALUATION_CONFIG = {
    "batch_size": 3,
    "min_score": 0.7,
    "timeout": 30
}