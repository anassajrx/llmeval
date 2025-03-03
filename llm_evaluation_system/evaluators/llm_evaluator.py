import logging
import time
from typing import List, Dict, Any
import queue
from threading import Lock

from config.settings import EVALUATION_CONFIG, RETRY_CONFIG
from core.exceptions import ModelEvaluationError
from evaluators.legal_assistant import LegalAssistant

logger = logging.getLogger(__name__)

class RequestQueue:
    """File d'attente pour les requêtes QCM"""
    def __init__(self, max_size: int = 100):
        self.queue = queue.Queue(maxsize=max_size)
        self.response_cache = {}
        self.lock = Lock()

    def add_request(self, qcm: Dict[str, Any], prompt_type: str = 'standard', retries: int = 0):
        """Ajoute une requête à la file d'attente"""
        self.queue.put((qcm, prompt_type, retries))

    def get_request(self):
        """Récupère une requête de la file d'attente"""
        return self.queue.get()

    def is_empty(self):
        """Vérifie si la file d'attente est vide"""
        return self.queue.empty()
        
    def get_from_cache(self, qcm: Dict[str, Any], prompt_type: str) -> str:
        """Récupère une réponse du cache si elle existe"""
        with self.lock:
            cache_key = f"{hash(qcm['question'])}_{prompt_type}"
            return self.response_cache.get(cache_key)
            
    def add_to_cache(self, qcm: Dict[str, Any], prompt_type: str, response: str):
        """Ajoute une réponse au cache"""
        with self.lock:
            cache_key = f"{hash(qcm['question'])}_{prompt_type}"
            self.response_cache[cache_key] = response

class LLMEvaluator:
    """Évaluateur principal pour les modèles de langage"""
    
    def __init__(self):
        """Initialise l'évaluateur avec l'Assistant Juridique"""
        self.legal_assistant = LegalAssistant()
        self.request_queue = RequestQueue()
        
        self.test_types = {
            'bias_test': self._test_bias_resistance,
            'integrity_test': self._test_integrity,
            'relevance_test': self._test_relevance,
            'legal_test': self._test_legal_compliance,
            'coherence_test': self._test_coherence
        }
        
        logger.info("LLMEvaluator initialized successfully")

    def evaluate_model(self, qcm_list: List[Dict[str, Any]], 
                      batch_size: int = EVALUATION_CONFIG["batch_size"],
                      test_mode: bool = True) -> Dict[str, Any]:
        """
        Évalue le modèle avec les QCM générés
        
        Args:
            qcm_list (List[Dict[str, Any]]): Liste des QCM pour l'évaluation
            batch_size (int): Taille des lots de traitement
            test_mode (bool): Si True, limite les tests avancés
            
        Returns:
            Dict[str, Any]: Résultats de l'évaluation
        """
        results = {
            'total_score': 0,
            'criteria_scores': {},
            'advanced_metrics': {},
            'details': [],
            'success_rate': 0,
            'error_count': 0
        }

        total_qcm = len(qcm_list)
        batches = [qcm_list[i:i + batch_size] for i in range(0, total_qcm, batch_size)]

        for batch_idx, batch in enumerate(batches):
            logger.info(f"Processing batch {batch_idx + 1}/{len(batches)}")
            
            for qcm in batch:
                try:
                    # Vérification du cache
                    cached_response = self.request_queue.get_from_cache(qcm, 'standard')
                    if cached_response:
                        response = cached_response
                    else:
                        # Demande à l'assistant juridique
                        response = self.legal_assistant.ask_question(qcm, 'standard')
                        self.request_queue.add_to_cache(qcm, 'standard', response)
                    
                    if response != 'ERROR':
                        standard_result = self._create_response_dict(qcm, response)
                        results['details'].append(standard_result)
                        
                        # En mode test, on saute les tests avancés
                        if not test_mode:
                            time.sleep(RETRY_CONFIG["base_delay"])
                            advanced_result = self._run_advanced_tests(qcm)
                            self._update_results(results, standard_result, advanced_result, qcm)
                        else:
                            # En mode test, on met à jour uniquement avec les résultats standards
                            self._update_results(results, standard_result, {}, qcm)
                    else:
                        results['error_count'] += 1

                except Exception as e:
                    logger.error(f"Error processing QCM: {str(e)}")
                    results['error_count'] += 1

            if batch_idx < len(batches) - 1:
                time.sleep(RETRY_CONFIG["base_delay"] * 2)

        self._calculate_final_metrics(results, total_qcm)
        return results

    def _test_bias_resistance(self, qcm: Dict[str, Any]) -> Dict[str, Any]:
        """Teste la résistance aux biais"""
        variations = [
            self._modify_gender_context(qcm),
            self._modify_cultural_context(qcm),
            self._modify_socioeconomic_context(qcm)
        ]

        results = []
        for variation in variations:
            result = self._process_single_qcm(variation, 'bias')
            results.append(result)

        return self._analyze_bias_results(results)

    def _test_integrity(self, qcm: Dict[str, Any]) -> Dict[str, Any]:
        """Teste l'intégrité"""
        modified_qcm = self._add_contradictory_information(qcm)
        result = self._process_single_qcm(modified_qcm, 'integrity')
        return self._analyze_integrity_result(result)

    def _test_relevance(self, qcm: Dict[str, Any]) -> Dict[str, Any]:
        """Teste la pertinence"""
        modified_qcm = self._modify_context_relevance(qcm)
        result = self._process_single_qcm(modified_qcm, 'standard')
        return self._analyze_relevance_result(result)

    def _test_legal_compliance(self, qcm: Dict[str, Any]) -> Dict[str, Any]:
        """Teste la conformité légale"""
        legal_variations = [
            self._add_jurisdiction_complexity(qcm),
            self._add_regulatory_requirements(qcm)
        ]

        results = []
        for variation in legal_variations:
            result = self._process_single_qcm(variation, 'legal')
            results.append(result)

        return self._analyze_legal_results(results)

    def _test_coherence(self, qcm: Dict[str, Any]) -> Dict[str, Any]:
        """Teste la cohérence"""
        modified_qcm = self._restructure_question(qcm)
        result = self._process_single_qcm(modified_qcm, 'standard')
        return self._analyze_coherence_result(result)

    def _process_single_qcm(self, qcm: Dict[str, Any], prompt_type: str) -> Dict[str, Any]:
        """
        Traite un seul QCM
        
        Args:
            qcm (Dict[str, Any]): QCM à traiter
            prompt_type (str): Type de prompt à utiliser
            
        Returns:
            Dict[str, Any]: Résultat du traitement
        """
        cached_response = self.request_queue.get_from_cache(qcm, prompt_type)
        if cached_response:
            response = cached_response
        else:
            response = self.legal_assistant.ask_question(qcm, prompt_type)
            self.request_queue.add_to_cache(qcm, prompt_type, response)
        
        if response != 'ERROR':
            return self._create_response_dict(qcm, response)
        
        return self._create_error_response(qcm)

    def _create_response_dict(self, qcm: Dict, response: str) -> Dict:
        """Crée un dictionnaire de réponse"""
        correct = response == qcm['correct_answer']
        return {
            'criterion': qcm['criterion'],
            'question': qcm['question'],
            'model_answer': response,
            'correct_answer': qcm['correct_answer'],
            'score': qcm['points'] if correct else 0,
            'max_points': qcm['points'],
            'status': 'success'
        }

    def _create_error_response(self, qcm: Dict) -> Dict:
        """Crée une réponse d'erreur"""
        return {
            'criterion': qcm['criterion'],
            'question': qcm['question'],
            'model_answer': 'ERROR',
            'correct_answer': qcm['correct_answer'],
            'score': 0,
            'max_points': qcm['points'],
            'status': 'error'
        }

    def _modify_gender_context(self, qcm: Dict) -> Dict:
        """Modifie le contexte pour le genre"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = qcm['question'] + " (Dans un contexte de parité hommes-femmes)"
        return modified_qcm

    def _modify_cultural_context(self, qcm: Dict) -> Dict:
        """Modifie le contexte culturel"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = qcm['question'] + " (Dans un contexte multiculturel)"
        return modified_qcm

    def _modify_socioeconomic_context(self, qcm: Dict) -> Dict:
        """Modifie le contexte socio-économique"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = qcm['question'] + " (Dans différents contextes socio-économiques)"
        return modified_qcm

    def _add_contradictory_information(self, qcm: Dict) -> Dict:
        """Ajoute des informations contradictoires"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = qcm['question'] + " (Malgré des informations contradictoires)"
        return modified_qcm

    def _modify_context_relevance(self, qcm: Dict) -> Dict:
        """Modifie le contexte pour la pertinence"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = "Dans un contexte différent : " + qcm['question']
        return modified_qcm

    def _add_jurisdiction_complexity(self, qcm: Dict) -> Dict:
        """Ajoute de la complexité juridictionnelle"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = qcm['question'] + " (Dans un contexte juridique international)"
        return modified_qcm

    def _add_regulatory_requirements(self, qcm: Dict) -> Dict:
        """Ajoute des exigences réglementaires"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = qcm['question'] + " (Selon les dernières réglementations)"
        return modified_qcm

    def _restructure_question(self, qcm: Dict) -> Dict:
        """Restructure la question"""
        modified_qcm = qcm.copy()
        modified_qcm['question'] = "En réorganisant le problème : " + qcm['question']
        return modified_qcm

    def _analyze_bias_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyse les résultats des tests de biais"""
        if not results:
            return {'status': 'error', 'score': 0}
        
        return {
            'status': 'success',
            'score': sum(r['score'] for r in results) / len(results),
            'consistency': self._calculate_consistency(results)
        }

    def _analyze_integrity_result(self, result: Dict) -> Dict[str, Any]:
        """Analyse le résultat du test d'intégrité"""
        return {
            'status': 'success',
            'score': result['score'],
            'integrity_maintained': result['model_answer'] == result['correct_answer']
        }

    def _analyze_relevance_result(self, result: Dict) -> Dict[str, Any]:
        """Analyse le résultat du test de pertinence"""
        return {
            'status': 'success',
            'score': result['score'],
            'context_awareness': result['model_answer'] == result['correct_answer']
        }

    def _analyze_legal_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Analyse les résultats des tests de conformité légale"""
        if not results:
            return {'status': 'error', 'score': 0}
        
        return {
            'status': 'success',
            'score': sum(r['score'] for r in results) / len(results),
            'compliance_level': self._calculate_compliance_level(results)
        }

    def _analyze_coherence_result(self, result: Dict) -> Dict[str, Any]:
        """Analyse le résultat du test de cohérence"""
        return {
            'status': 'success',
            'score': result['score'],
            'logical_consistency': result['model_answer'] == result['correct_answer']
        }

    def _calculate_consistency(self, results: List[Dict]) -> float:
        """Calcule la cohérence des résultats"""
        if not results:
            return 0.0
        correct_answers = sum(1 for r in results if r['model_answer'] == r['correct_answer'])
        return (correct_answers / len(results)) * 100

    def _calculate_compliance_level(self, results: List[Dict]) -> float:
        """Calcule le niveau de conformité"""
        if not results:
            return 0.0
        return sum(r['score'] for r in results) / (len(results) * results[0]['max_points']) * 100 if results else 0

    def _run_advanced_tests(self, qcm: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute les tests avancés
        
        Args:
            qcm (Dict[str, Any]): QCM à tester
            
        Returns:
            Dict[str, Any]: Résultats des tests avancés
        """
        advanced_results = {}
        
        for test_name, test_func in self.test_types.items():
            try:
                result = test_func(qcm)
                advanced_results[test_name] = result
                logger.debug(f"Completed {test_name} with result: {result}")
                time.sleep(RETRY_CONFIG["base_delay"])
            except Exception as e:
                logger.error(f"Error in {test_name}: {str(e)}")
                advanced_results[test_name] = {'status': 'error', 'score': 0}
                
        return advanced_results

    def _update_results(self, results: Dict, standard_result: Dict, 
                       advanced_result: Dict, qcm: Dict) -> None:
        """
        Met à jour les résultats avec les tests standard et avancés
        
        Args:
            results (Dict): Résultats globaux à mettre à jour
            standard_result (Dict): Résultat du test standard
            advanced_result (Dict): Résultats des tests avancés
            qcm (Dict): QCM évalué
        """
        criterion = qcm['criterion']

        if criterion not in results['criteria_scores']:
            results['criteria_scores'][criterion] = {
                'score': 0,
                'total': 0,
                'questions_count': 0,
                'success_count': 0,
                'advanced_metrics': {}
            }

        criteria_stats = results['criteria_scores'][criterion]

        if standard_result['status'] == 'success':
            criteria_stats['success_count'] += 1
            criteria_stats['score'] += standard_result['score']

        criteria_stats['total'] += standard_result['max_points']
        criteria_stats['questions_count'] += 1
        criteria_stats['advanced_metrics'].update(advanced_result)

    def _calculate_final_metrics(self, results: Dict, total_qcm: int) -> None:
        """
        Calcule les métriques finales
        
        Args:
            results (Dict): Résultats à finaliser
            total_qcm (int): Nombre total de QCM
        """
        successful_tests = total_qcm - results['error_count']
        results['success_rate'] = (successful_tests / total_qcm) * 100 if total_qcm > 0 else 0

        total_score = 0
        total_possible = 0
        for criterion_stats in results['criteria_scores'].values():
            total_score += criterion_stats['score']
            total_possible += criterion_stats['total']

        results['total_score'] = (total_score / total_possible * 100) if total_possible > 0 else 0