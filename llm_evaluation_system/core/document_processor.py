import fitz  # PyMuPDF
import logging
from pathlib import Path
from typing import List, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config.settings import CHUNK_CONFIG
from core.exceptions import DocumentProcessingError
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Classe pour le traitement des documents PDF et leur découpage en chunks"""
    
    def __init__(self, chunk_size: int = CHUNK_CONFIG["chunk_size"], 
                 chunk_overlap: int = CHUNK_CONFIG["chunk_overlap"]):
        """
        Initialise le processeur de documents
        
        Args:
            chunk_size (int): Taille des chunks de texte
            chunk_overlap (int): Chevauchement entre les chunks
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        logger.info(f"DocumentProcessor initialized with chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")

    def load_pdf(self, file_path: str) -> str:
        """
        Charge et extrait le texte d'un fichier PDF
        
        Args:
            file_path (str): Chemin vers le fichier PDF
            
        Returns:
            str: Texte extrait du PDF
            
        Raises:
            DocumentProcessingError: Si une erreur survient lors du traitement
        """
        try:
            logger.info(f"Loading PDF from {file_path}")
            doc = fitz.open(file_path)
            text = ""
            for page_num, page in enumerate(doc):
                text += page.get_text()
                logger.debug(f"Processed page {page_num + 1}/{len(doc)}")
            return text
        except Exception as e:
            error_msg = f"Error loading PDF from {file_path}: {str(e)}"
            logger.error(error_msg)
            raise DocumentProcessingError(error_msg)

    def process_documents(self, file_paths: List[str]) -> List[str]:
        """
        Traite plusieurs documents et retourne les chunks
        
        Args:
            file_paths (List[str]): Liste des chemins des fichiers à traiter
            
        Returns:
            List[str]: Liste des chunks de texte
            
        Raises:
            DocumentProcessingError: Si une erreur survient lors du traitement
        """
        try:
            logger.info(f"Processing {len(file_paths)} documents")
            all_text = ""
            for file_path in file_paths:
                if Path(file_path).suffix.lower() == '.pdf':
                    all_text += self.load_pdf(file_path)
                    
            chunks = self.text_splitter.split_text(all_text)
            logger.info(f"Generated {len(chunks)} chunks from documents")
            return chunks
            
        except Exception as e:
            error_msg = f"Error processing documents: {str(e)}"
            logger.error(error_msg)
            raise DocumentProcessingError(error_msg)

    def validate_document(self, file_path: str) -> bool:
        """
        Valide qu'un document peut être traité
        
        Args:
            file_path (str): Chemin vers le fichier
            
        Returns:
            bool: True si le document est valide
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return False
            if path.suffix.lower() != '.pdf':
                logger.warning(f"Unsupported file format: {path.suffix}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating document {file_path}: {str(e)}")
            return False