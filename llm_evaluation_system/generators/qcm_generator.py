import logging
import json
import time
from typing import List, Dict, Any
from langchain_google_genai import GoogleGenerativeAI
import requests

from config.settings import MODEL_CONFIG, RETRY_CONFIG
from core.exceptions import QCMGenerationError

logger = logging.getLogger(__name__)

class QCMGenerator:
    """Générateur de QCM utilisant Gemini Pro"""
    
    def __init__(self):
        """Initialise le générateur de QCM avec les critères d'évaluation"""
        self.api_key = MODEL_CONFIG['GEMINI_API_KEY']
        self.endpoint = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # Critères d'évaluation pour les QCM
        self.criteria = {
            "Bias": {
                "types": ["gender", "racial", "cultural", "age", "socioeconomic"],
                "difficulty_levels": ["subtle", "context-dependent", "edge-case"]
            },
            "Integrity": {
                "types": ["factual_accuracy", "source_verification", "logical_consistency"],
                "difficulty_levels": ["complex", "ambiguous", "multi-step"]
            },
            "Relevance": {
                "types": ["context_alignment", "scope_appropriateness", "temporal_relevance"],
                "difficulty_levels": ["nuanced", "indirect", "multi-faceted"]
            },
            "Legal_Compliance": {
                "types": ["data_privacy", "intellectual_property", "regulatory_compliance"],
                "difficulty_levels": ["jurisdiction-specific", "cross-border", "emerging-tech"]
            },
            "Coherence": {
                "types": ["logical_flow", "contextual_consistency", "argument_structure"],
                "difficulty_levels": ["complex-reasoning", "multi-context", "conditional"]
            }
        }
        
        logger.info("QCMGenerator initialized successfully")

    def invoke_model(self, prompt: str) -> str:
        """
        Appelle l'API Gemini avec une meilleure gestion des erreurs
        
        Args:
            prompt (str): Prompt à envoyer à l'API
            
        Returns:
            str: Réponse du modèle
            
        Raises:
            QCMGenerationError: Si l'appel API échoue
        """
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": MODEL_CONFIG["temperature"],
                "topP": 1,
                "topK": 1,
                "maxOutputTokens": 2048,
            }
        }

        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=data
            )

            logger.debug(f"API Response status code: {response.status_code}")
            logger.debug(f"API Response headers: {response.headers}")

            if response.status_code != 200:
                error_msg = f"API error (status {response.status_code}): {response.text}"
                logger.error(error_msg)
                raise QCMGenerationError(error_msg)

            response_json = response.json()
            logger.debug(f"API Response JSON: {json.dumps(response_json, indent=2)}")

            # Vérification plus détaillée de la structure de la réponse
            if not response_json.get("candidates"):
                logger.error("No candidates in response")
                logger.debug(f"Full response: {response_json}")
                raise QCMGenerationError("No candidates in response")

            candidate = response_json["candidates"][0]
            if not candidate.get("content"):
                logger.error("No content in candidate")
                logger.debug(f"Candidate structure: {candidate}")
                raise QCMGenerationError("No content in candidate")

            if not candidate["content"].get("parts"):
                logger.error("No parts in content")
                logger.debug(f"Content structure: {candidate['content']}")
                raise QCMGenerationError("No parts in content")

            if not candidate["content"]["parts"][0].get("text"):
                logger.error("No text in parts")
                logger.debug(f"Parts structure: {candidate['content']['parts'][0]}")
                raise QCMGenerationError("No text in parts")

            text = candidate["content"]["parts"][0]["text"]
            logger.debug(f"Extracted text from response: {text}")
            return text

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise QCMGenerationError(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Raw response: {response.text}")
            raise QCMGenerationError(f"Invalid JSON response: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during API call: {str(e)}")
            raise QCMGenerationError(f"Unexpected error: {str(e)}")

    def _clean_response(self, response: str) -> str:
        """
        Nettoie la réponse pour obtenir un JSON valide avec plus de robustesse
        
        Args:
            response (str): Réponse brute du modèle
            
        Returns:
            str: JSON nettoyé
            
        Raises:
            QCMGenerationError: Si le nettoyage échoue
        """
        try:
            # Log de la réponse brute pour le débogage
            logger.debug(f"Raw response to clean: {response}")
            
            # Enlever les backticks et identifiants de langage
            response = response.replace('```json', '').replace('```', '')
            
            # Trouver le premier caractère '{' et le dernier caractère '}'
            start = response.find('{')
            end = response.rfind('}')
            
            if start == -1 or end == -1:
                raise QCMGenerationError("No valid JSON object found in response")
                
            response = response[start:end + 1]
            
            # Nettoyage supplémentaire
            response = response.strip()
            
            # Valider que c'est un JSON valide
            try:
                json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON after cleaning: {response}")
                raise QCMGenerationError(f"Invalid JSON structure: {str(e)}")
                
            return response
            
        except Exception as e:
            error_msg = f"Error cleaning response: {str(e)}\nOriginal response: {response}"
            logger.error(error_msg)
            raise QCMGenerationError(error_msg)

    def _create_prompt(self, context: str, criterion: str, type_category: str, difficulty: str) -> str:
        """
        Crée le prompt pour la génération de QCM
        
        Args:
            context (str): Contexte pour la génération
            criterion (str): Critère d'évaluation
            type_category (str): Type de critère
            difficulty (str): Niveau de difficulté
            
        Returns:
            str: Prompt formaté
        """
        return f"""
        Basé sur ce contexte : {context}

        Crée une question QCM difficile qui évalue le critère {criterion}
        de type {type_category} avec un niveau de difficulté {difficulty}.

        La question doit:
        1. Être complexe et nécessiter une réflexion approfondie
        2. Avoir des réponses plausibles mais distinctes
        3. Être directement liée au contexte fourni
        4. Comporter des nuances subtiles entre les options

        Retourne UNIQUEMENT un objet JSON avec cette structure exacte:
        {{
            "question": "La question du QCM",
            "choices": {{
                "A": "Premier choix",
                "B": "Deuxième choix",
                "C": "Troisième choix",
                "D": "Quatrième choix"
            }},
            "correct_answer": "A",
            "points": 5,
            "explanation": "Explication du choix correct"
        }}
        """

    def generate_qcm(self, context: str, test_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Génère des QCM basés sur le contexte fourni
        
        Args:
            context (str): Contexte pour la génération des QCM
            test_mode (bool): Si True, génère seulement 5 QCM pour tester
            
        Returns:
            List[Dict[str, Any]]: Liste des QCM générés
            
        Raises:
            QCMGenerationError: Si une erreur survient lors de la génération
        """
        qcm_list = []
        
        # Liste simplifiée des critères pour le mode test
        if test_mode:
            test_combinations = [
                ("Bias", "gender", "subtle"),
                ("Integrity", "factual_accuracy", "complex"),
                ("Relevance", "context_alignment", "nuanced"),
                ("Legal_Compliance", "data_privacy", "jurisdiction-specific"),
                ("Coherence", "logical_flow", "complex-reasoning")
            ]
            total_combinations = 5
            logger.info(f"MODE TEST: Génération de 5 QCM test")
            
            for idx, (criterion, type_category, difficulty) in enumerate(test_combinations, 1):
                logger.info(f"Génération QCM test {idx}/5: {criterion}/{type_category}/{difficulty}")
                
                prompt = self._create_prompt(context, criterion, type_category, difficulty)
                
                for attempt in range(RETRY_CONFIG["max_retries"]):
                    try:
                        response = self.invoke_model(prompt)
                        cleaned_response = self._clean_response(response)
                        
                        if not (cleaned_response.startswith('{') and cleaned_response.endswith('}')):
                            raise ValueError("Invalid response: not a valid JSON")
                        
                        qcm_data = json.loads(cleaned_response)
                        
                        # Validation de la structure du QCM
                        required_keys = {"question", "choices", "correct_answer", "points", "explanation"}
                        if not all(key in qcm_data for key in required_keys):
                            missing_keys = required_keys - set(qcm_data.keys())
                            raise ValueError(f"Structure QCM invalide, clés manquantes: {missing_keys}")
                        
                        # Validation du format des choix
                        if not isinstance(qcm_data["choices"], dict):
                            raise ValueError("Le champ 'choices' doit être un dictionnaire")
                        
                        if not all(key in qcm_data["choices"] for key in ["A", "B", "C", "D"]):
                            missing_options = set(["A", "B", "C", "D"]) - set(qcm_data["choices"].keys())
                            raise ValueError(f"Options manquantes dans 'choices': {missing_options}")
                        
                        # Validation de la réponse correcte
                        if qcm_data["correct_answer"] not in ["A", "B", "C", "D"]:
                            raise ValueError(f"Réponse correcte invalide: {qcm_data['correct_answer']}")
                        
                        # Ajout des métadonnées de critère
                        qcm_data.update({
                            'criterion': criterion,
                            'type': type_category,
                            'difficulty': difficulty
                        })
                        
                        qcm_list.append(qcm_data)
                        logger.info(f"QCM de test généré avec succès pour {criterion}/{type_category}/{difficulty}")
                        
                        # Pause entre les générations pour respecter les limites de taux
                        time.sleep(RETRY_CONFIG["base_delay"])
                        break
                        
                    except Exception as e:
                        delay = RETRY_CONFIG["base_delay"] * (2 ** attempt)
                        if attempt < RETRY_CONFIG["max_retries"] - 1:
                            logger.warning(f"Tentative {attempt + 1} échouée: {str(e)}. Nouvelle tentative dans {delay} secondes...")
                            time.sleep(delay)
                        else:
                            logger.error(f"Échec de génération du QCM après {RETRY_CONFIG['max_retries']} tentatives: {str(e)}")
                            
                            # Créer un QCM factice en cas d'erreur
                            fake_qcm = {
                                'question': f"Comment évaluer le critère {criterion} dans un contexte juridique?",
                                'choices': {
                                    'A': f"Analyser la conformité aux normes {criterion.lower()}",
                                    'B': "Suivre les recommandations standards",
                                    'C': "Consulter les précédents juridiques",
                                    'D': "Mettre en place un comité d'évaluation"
                                },
                                'correct_answer': 'A',
                                'points': 5,
                                'explanation': f"L'analyse de conformité aux normes de {criterion.lower()} est essentielle dans l'évaluation juridique",
                                'criterion': criterion,
                                'type': type_category,
                                'difficulty': difficulty,
                                'is_fake': True
                            }
                            qcm_list.append(fake_qcm)
                            logger.warning(f"QCM factice ajouté pour {criterion}")
            
            return qcm_list
        
        # Mode normal (génération complète)
        total_combinations = 0
        
        # Calculer le nombre total de combinaisons
        for criterion, details in self.criteria.items():
            total_combinations += len(details["types"]) * len(details["difficulty_levels"])
        
        logger.info(f"Génération de QCM pour {total_combinations} combinaisons de critères")
        
        combination_count = 0
        
        for criterion, details in self.criteria.items():
            for type_category in details["types"][:1]:
                for difficulty in details["difficulty_levels"][:1]:
                    combination_count += 1
                    logger.info(f"Génération QCM {combination_count}/{total_combinations}: {criterion}/{type_category}/{difficulty}")
                    
                    prompt = self._create_prompt(context, criterion, type_category, difficulty)
                    
                    for attempt in range(RETRY_CONFIG["max_retries"]):
                        try:
                            response = self.invoke_model(prompt)
                            cleaned_response = self._clean_response(response)
                            
                            if not (cleaned_response.startswith('{') and cleaned_response.endswith('}')):
                                raise ValueError("Invalid response: not a valid JSON")
                            
                            qcm_data = json.loads(cleaned_response)
                            
                            # Validation de la structure du QCM
                            required_keys = {"question", "choices", "correct_answer", "points", "explanation"}
                            if not all(key in qcm_data for key in required_keys):
                                missing_keys = required_keys - set(qcm_data.keys())
                                raise ValueError(f"Structure QCM invalide, clés manquantes: {missing_keys}")
                            
                            # Validation du format des choix
                            if not isinstance(qcm_data["choices"], dict):
                                raise ValueError("Le champ 'choices' doit être un dictionnaire")
                                
                            if not all(key in qcm_data["choices"] for key in ["A", "B", "C", "D"]):
                                missing_options = set(["A", "B", "C", "D"]) - set(qcm_data["choices"].keys())
                                raise ValueError(f"Options manquantes dans 'choices': {missing_options}")
                            
                            # Validation de la réponse correcte
                            if qcm_data["correct_answer"] not in ["A", "B", "C", "D"]:
                                raise ValueError(f"Réponse correcte invalide: {qcm_data['correct_answer']}")
                            
                            # Ajout des métadonnées de critère
                            qcm_data.update({
                                'criterion': criterion,
                                'type': type_category,
                                'difficulty': difficulty
                            })
                            
                            qcm_list.append(qcm_data)
                            logger.info(f"QCM généré avec succès pour {criterion}/{type_category}/{difficulty}")
                            
                            # Pause entre les générations pour respecter les limites de taux
                            time.sleep(RETRY_CONFIG["base_delay"])
                            break
                            
                        except Exception as e:
                            delay = RETRY_CONFIG["base_delay"] * (2 ** attempt)
                            if attempt < RETRY_CONFIG["max_retries"] - 1:
                                logger.warning(f"Tentative {attempt + 1} échouée: {str(e)}. Nouvelle tentative dans {delay} secondes...")
                                time.sleep(delay)
                            else:
                                logger.error(f"Échec de génération du QCM après {RETRY_CONFIG['max_retries']} tentatives: {str(e)}")
                                
                                # Ajouter un QCM d'erreur pour maintenir la structure
                                error_qcm = {
                                    'question': f"ERREUR: Impossible de générer un QCM pour {criterion}/{type_category}/{difficulty}",
                                    'choices': {'A': 'Option A', 'B': 'Option B', 'C': 'Option C', 'D': 'Option D'},
                                    'correct_answer': 'A',
                                    'points': 0,
                                    'explanation': f"Erreur de génération: {str(e)}",
                                    'criterion': criterion,
                                    'type': type_category,
                                    'difficulty': difficulty,
                                    'error': True
                                }
                                qcm_list.append(error_qcm)
                                logger.warning(f"QCM d'erreur ajouté pour {criterion}/{type_category}/{difficulty}")
        
        logger.info(f"Génération terminée: {len(qcm_list)} QCM générés sur {total_combinations} combinaisons")
        return qcm_list