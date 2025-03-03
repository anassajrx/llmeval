import logging
import time
from pathlib import Path
from typing import List, Dict, Any

# Import des composants du système
from config.settings import INPUT_DIR, OUTPUT_DIR
from core.document_processor import DocumentProcessor
from core.embeddings_manager import EmbeddingsManager
from generators.qcm_generator import QCMGenerator
from evaluators.llm_evaluator import LLMEvaluator
from evaluators.legal_assistant import LegalAssistant
from evaluators.advanced_llm_testing import AdvancedLLMTesting
from generators.report_generator import ReportGenerator
from utils.helpers import (
    save_json, 
    create_output_directories, 
    format_duration
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMEvaluationSystem:
    """Système principal d'évaluation des LLM"""
    
    def __init__(self):
        """Initialise le système avec tous ses composants"""
        try:
            logger.info("Initializing LLM Evaluation System...")
            
            # Création des répertoires
            self.directories = create_output_directories(OUTPUT_DIR)
            
            # Initialisation des composants
            self.doc_processor = DocumentProcessor()
            self.embeddings_manager = EmbeddingsManager()
            self.qcm_generator = QCMGenerator()
            self.llm_evaluator = LLMEvaluator()
            self.advanced_testing = AdvancedLLMTesting()
            self.report_generator = ReportGenerator()
            self.legal_assistant = LegalAssistant()
            
            logger.info("System initialized successfully")
            
        except Exception as e:
            logger.critical(f"Failed to initialize system: {str(e)}")
            raise

    def process_documents(self, file_paths: List[str]) -> List[str]:
        """
        Traite les documents et génère les chunks
        
        Args:
            file_paths: Liste des chemins des fichiers à traiter
            
        Returns:
            List[str]: Liste des chunks générés
        """
        logger.info(f"Processing {len(file_paths)} documents...")
        #return self.doc_processor.process_documents(file_paths)
        return self.doc_processor.process_documents(file_paths)[:1] 


    def generate_and_store_embeddings(self, chunks: List[str]):
        """
        Génère et stocke les embeddings pour les chunks
        
        Args:
            chunks: Liste des chunks de texte
        """
        logger.info("Generating and storing embeddings...")
        self.embeddings_manager.store_embeddings(chunks)

    def generate_qcm(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Génère les QCM à partir des chunks
        
        Args:
            chunks: Liste des chunks de texte
            
        Returns:
            List[Dict[str, Any]]: Liste des QCM générés
        """
        logger.info("Generating QCM...")
        qcm_list = []
        
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}...")
            chunk_qcm = self.qcm_generator.generate_qcm(chunk)
            qcm_list.extend(chunk_qcm)
            
        return qcm_list

    def evaluate_model(self, qcm_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Évalue le modèle avec les QCM générés
        
        Args:
            qcm_list: Liste des QCM pour l'évaluation
            
        Returns:
            Dict[str, Any]: Résultats de l'évaluation
        """
        logger.info("Starting model evaluation...")
        
        # Évaluation standard
        evaluation_results = self.llm_evaluator.evaluate_model(qcm_list)
        
        # Tests avancés
        advanced_results = {
            'bias_resistance': self.advanced_testing.test_bias_resistance(qcm_list),
            'integrity': self.advanced_testing.test_integrity_under_pressure(qcm_list),
            'legal_compliance': self.advanced_testing.test_legal_compliance_edge_cases(qcm_list)
        }
        
        evaluation_results['advanced_testing'] = advanced_results
        return evaluation_results

    def generate_reports(self, evaluation_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Génère les rapports d'évaluation
        
        Args:
            evaluation_results: Résultats de l'évaluation
            
        Returns:
            Dict[str, str]: Chemins des rapports générés
        """
        logger.info("Generating evaluation reports...")
        return self.report_generator.generate_report(evaluation_results)

    def run_evaluation(self, input_files: List[str], test_mode: bool = False) -> Dict[str, Any]:
        """
        Exécute le processus complet d'évaluation
        
        Args:
            input_files: Liste des fichiers à traiter
            test_mode: Si True, génère seulement 5 QCM pour tester
            
        Returns:
            Dict[str, Any]: Résultats complets de l'évaluation
        """
        start_time = time.time()
        logger.info("Starting evaluation process...")
        
        try:
            # 1. Traitement des documents
            chunks = self.process_documents(input_files)
            
            # 2. Génération et stockage des embeddings
            self.generate_and_store_embeddings(chunks)
            
            # 3. Génération des QCM
            qcm_list = self.qcm_generator.generate_qcm(chunks[0], test_mode=test_mode)
            
            # Sauvegarde des QCM générés
            qcm_path = save_json(qcm_list, "qcm", self.directories['qcm'])
            logger.info(f"QCM saved to {qcm_path}")
            
            # 4. Évaluation du modèle
            evaluation_results = self.llm_evaluator.evaluate_model(qcm_list, test_mode=test_mode)
            
            # 5. Génération des rapports
            report_paths = self.report_generator.generate_report(evaluation_results)
            
            # Calcul de la durée totale
            duration = time.time() - start_time
            
            # Résultats finaux
            final_results = {
                'evaluation_results': evaluation_results,
                'report_paths': report_paths,
                'qcm': qcm_list,  # Ajouter les QCM aux résultats pour faciliter leur affichage
                'metadata': {
                    'duration': format_duration(duration),
                    'chunks_processed': len(chunks),
                    'qcm_generated': len(qcm_list),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                }
            }
            
            logger.info(f"Evaluation completed in {format_duration(duration)}")
            return final_results
            
        except Exception as e:
            logger.error(f"Error during evaluation: {str(e)}")
            raise

def main():
    """Point d'entrée principal du programme"""
    try:
        # Initialisation du système
        system = LLMEvaluationSystem()
        
         # Récupération des fichiers d'entrée - MODIFICATION ICI
        input_files = list(Path(INPUT_DIR).glob('*.pdf'))  # Cherche les .pdf
        input_files.extend(list(Path(INPUT_DIR).glob('*.PDF')))  # Cherche aussi les .PDF majuscules
        
        logger.info(f"Looking for PDF files in: {INPUT_DIR}")
        logger.info(f"Found files: {[f.name for f in input_files]}")
        
        if not input_files:
            logger.error(f"No PDF files found in input directory: {INPUT_DIR}")
            return
        
        
        # Exécution de l'évaluation
        results = system.run_evaluation([str(f) for f in input_files])
        
        # Affichage des résultats
        print("\n=== Evaluation Results ===")
        print(f"Documents processed: {len(input_files)}")
        print(f"QCM generated: {results['metadata']['qcm_generated']}")
        print(f"Duration: {results['metadata']['duration']}")
        print("\nReport files generated:")
        for report_type, path in results['report_paths'].items():
            print(f"- {report_type}: {path}")
            
    except Exception as e:
        logger.critical(f"Critical error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main()