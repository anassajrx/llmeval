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
        return self.doc_processor.process_documents(file_paths)[:1]

    def generate_and_store_embeddings(self, chunks: List[str]):
        """
        Génère et stocke les embeddings pour les chunks
        
        Args:
            chunks: Liste des chunks de texte
        """
        logger.info("Generating and storing embeddings...")
        self.embeddings_manager.store_embeddings(chunks)

    def generate_qcm(self, context: str, selected_criteria: List[str] = None, test_mode: bool = False, num_generic_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Génère les QCM à partir du contexte
        
        Args:
            context: Contexte pour la génération
            selected_criteria: Critères sélectionnés pour les QCM (None = QCM génériques)
            test_mode: Si True, génère un nombre réduit de QCM
            num_generic_questions: Nombre de questions génériques si pas de critères
            
        Returns:
            List[Dict[str, Any]]: Liste des QCM générés
        """
        logger.info(f"Generating QCM with {'generic mode' if not selected_criteria else 'selected criteria: ' + str(selected_criteria)}...")
        return self.qcm_generator.generate_qcm(context, selected_criteria, test_mode, num_generic_questions)

    def evaluate_model(self, qcm_list: List[Dict[str, Any]], advanced_criteria: List[str] = None) -> Dict[str, Any]:
        """
        Évalue le modèle avec les QCM générés
        
        Args:
            qcm_list: Liste des QCM pour l'évaluation
            advanced_criteria: Critères pour les tests avancés (None = tests standard uniquement)
            
        Returns:
            Dict[str, Any]: Résultats de l'évaluation
        """
        logger.info("Starting model evaluation...")
        
        # Évaluation avec paramètres avancés si spécifiés
        evaluation_results = self.llm_evaluator.evaluate_model(qcm_list, advanced_criteria=advanced_criteria)
        
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

    def run_evaluation(self, input_files: List[str], 
                     selected_criteria: List[str] = None, 
                     advanced_criteria: List[str] = None,
                     test_mode: bool = False) -> Dict[str, Any]:
        """
        Exécute le processus complet d'évaluation
        
        Args:
            input_files: Liste des fichiers à traiter
            selected_criteria: Critères sélectionnés pour la génération de QCM
            advanced_criteria: Critères pour les tests avancés d'évaluation
            test_mode: Si True, génère un nombre réduit de QCM
            
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
            qcm_list = self.generate_qcm(
                chunks[0], 
                selected_criteria=selected_criteria, 
                test_mode=test_mode
            )
            
            # Sauvegarde des QCM générés
            qcm_path = save_json(qcm_list, "qcm", self.directories['qcm'])
            logger.info(f"QCM saved to {qcm_path}")
            
            # 4. Évaluation du modèle
            evaluation_results = self.evaluate_model(qcm_list, advanced_criteria=advanced_criteria)
            
            # 5. Génération des rapports
            report_paths = self.report_generator.generate_report(evaluation_results)
            
            # Calcul de la durée totale
            duration = time.time() - start_time
            
            # Résultats finaux
            final_results = {
                'evaluation_results': evaluation_results,
                'report_paths': report_paths,
                'qcm': qcm_list,
                'metadata': {
                    'duration': format_duration(duration),
                    'chunks_processed': len(chunks),
                    'qcm_generated': len(qcm_list),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'selected_criteria': selected_criteria,
                    'advanced_criteria': advanced_criteria
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
        
        # Récupération des fichiers d'entrée
        input_files = list(Path(INPUT_DIR).glob('*.pdf'))  # Cherche les .pdf
        input_files.extend(list(Path(INPUT_DIR).glob('*.PDF')))  # Cherche aussi les .PDF majuscules
        
        logger.info(f"Looking for PDF files in: {INPUT_DIR}")
        logger.info(f"Found files: {[f.name for f in input_files]}")
        
        if not input_files:
            logger.error(f"No PDF files found in input directory: {INPUT_DIR}")
            return
        
        # Exécution de l'évaluation avec paramètres par défaut (génériques sans tests avancés)
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