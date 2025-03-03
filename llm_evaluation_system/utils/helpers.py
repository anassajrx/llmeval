import logging
import json
from pathlib import Path
from typing import Dict, Any, Union, List
from datetime import datetime

logger = logging.getLogger(__name__)

def save_json(data: Union[Dict, List], 
             filename: str, 
             output_dir: Path) -> Path:
    """
    Sauvegarde des données au format JSON
    
    Args:
        data: Données à sauvegarder
        filename: Nom du fichier
        output_dir: Répertoire de sortie
        
    Returns:
        Path: Chemin du fichier sauvegardé
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = output_dir / f"{filename}_{timestamp}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Successfully saved JSON to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error saving JSON: {str(e)}")
        raise

def load_json(file_path: Union[str, Path]) -> Union[Dict, List]:
    """
    Charge des données depuis un fichier JSON
    
    Args:
        file_path: Chemin du fichier à charger
        
    Returns:
        Dict or List: Données chargées
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded JSON from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON: {str(e)}")
        raise

def validate_qcm_format(qcm: Dict[str, Any]) -> bool:
    """
    Valide le format d'un QCM
    
    Args:
        qcm: QCM à valider
        
    Returns:
        bool: True si le format est valide
    """
    required_keys = {
        'question', 
        'choices', 
        'correct_answer', 
        'points', 
        'explanation'
    }
    
    try:
        # Vérification des clés requises
        if not all(key in qcm for key in required_keys):
            logger.warning("Missing required keys in QCM")
            return False
            
        # Vérification des choix
        if not isinstance(qcm['choices'], dict) or not all(
            key in qcm['choices'] for key in ['A', 'B', 'C', 'D']):
            logger.warning("Invalid choices format in QCM")
            return False
            
        # Vérification de la réponse correcte
        if qcm['correct_answer'] not in ['A', 'B', 'C', 'D']:
            logger.warning("Invalid correct answer in QCM")
            return False
            
        # Vérification des points
        if not isinstance(qcm['points'], (int, float)) or qcm['points'] <= 0:
            logger.warning("Invalid points value in QCM")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error validating QCM: {str(e)}")
        return False

def format_duration(seconds: float) -> str:
    """
    Formate une durée en secondes en format lisible
    
    Args:
        seconds: Nombre de secondes
        
    Returns:
        str: Durée formatée
    """
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}s")
        
    return " ".join(parts)

def create_output_directories(base_dir: Path) -> Dict[str, Path]:
    """
    Crée les répertoires de sortie nécessaires
    
    Args:
        base_dir: Répertoire de base
        
    Returns:
        Dict[str, Path]: Dictionnaire des chemins créés
    """
    try:
        directories = {
            'qcm': base_dir / 'qcm',
            'results': base_dir / 'results',
            'reports': base_dir / 'reports',
            'viz': base_dir / 'visualizations'
        }
        
        for dir_path in directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {dir_path}")
            
        return directories
        
    except Exception as e:
        logger.error(f"Error creating directories: {str(e)}")
        raise

def clean_text(text: str) -> str:
    """
    Nettoie et normalise un texte
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        str: Texte nettoyé
    """
    try:
        # Suppression des espaces multiples
        text = ' '.join(text.split())
        
        # Suppression des caractères spéciaux en début/fin
        text = text.strip('.,;:!?')
        
        # Normalisation des sauts de ligne
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Error cleaning text: {str(e)}")
        return text

def get_file_info(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Obtient les informations sur un fichier
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        Dict[str, Any]: Informations sur le fichier
    """
    try:
        path = Path(file_path)
        stats = path.stat()
        
        return {
            'name': path.name,
            'extension': path.suffix,
            'size': stats.st_size,
            'created': datetime.fromtimestamp(stats.st_ctime),
            'modified': datetime.fromtimestamp(stats.st_mtime),
            'is_file': path.is_file(),
            'is_dir': path.is_dir()
        }
        
    except Exception as e:
        logger.error(f"Error getting file info: {str(e)}")
        raise