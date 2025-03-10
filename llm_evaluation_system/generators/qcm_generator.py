import logging
import json
import time
from typing import List, Dict, Any
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
        
        # Prompt générique puissant pour générer des QCM de qualité sans critères spécifiques
        self.generic_prompt_template = """
        Basé sur ce contexte : {context}

        Crée une question QCM difficile et de haute qualité qui évalue la compréhension approfondie du contexte. 
        
        La question doit:
        1. Être complexe et nécessiter une réflexion approfondie
        2. Avoir des réponses plausibles mais distinctes
        3. Être directement liée au contexte fourni
        4. Comporter des nuances subtiles entre les options
        5. Tester la compréhension conceptuelle plutôt que la simple mémorisation de faits
        6. Être formulée clairement et sans ambiguïté

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

    def _create_criteria_prompt(self, context: str, criterion: str, type_category: str, difficulty: str) -> str:
        """
        Crée le prompt pour la génération de QCM avec critères spécifiques
        
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

    def generate_generic_qcm(self, context: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Génère des QCM génériques sans critères spécifiques
        
        Args:
            context (str): Contexte pour la génération
            num_questions (int): Nombre de questions à générer
            
        Returns:
            List[Dict[str, Any]]: Liste des QCM générés
        """
        qcm_list = []
        prompt = self.generic_prompt_template.format(context=context)
        
        logger.info(f"Generating {num_questions} generic QCMs...")
        
        for i in range(num_questions):
            logger.info(f"Generating generic QCM {i+1}/{num_questions}")
            
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
                    
                    # Ajout des métadonnées génériques
                    qcm_data.update({
                        'criterion': "Generic",
                        'type': "standard",
                        'difficulty': "medium"
                    })
                    
                    qcm_list.append(qcm_data)
                    logger.info(f"Generic QCM {i+1} generated successfully")
                    
                    # Pause entre les générations pour respecter les limites de taux
                    time.sleep(RETRY_CONFIG["base_delay"])
                    break
                    
                except Exception as e:
                    delay = RETRY_CONFIG["base_delay"] * (2 ** attempt)
                    if attempt < RETRY_CONFIG["max_retries"] - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error(f"Failed to generate QCM after {RETRY_CONFIG['max_retries']} attempts: {str(e)}")
                        
                        # Créer un QCM factice en cas d'erreur
                        fake_qcm = {
                            'question': f"Question générique {i+1} (échec de génération)",
                            'choices': {
                                'A': "Option A",
                                'B': "Option B",
                                'C': "Option C",
                                'D': "Option D"
                            },
                            'correct_answer': 'A',
                            'points': 5,
                            'explanation': "QCM factice créé suite à une erreur de génération",
                            'criterion': "Generic",
                            'type': "standard",
                            'difficulty': "medium",
                            'is_fake': True
                        }
                        qcm_list.append(fake_qcm)
                        logger.warning(f"Added fake generic QCM due to generation error")
        
        return qcm_list

    def generate_criteria_qcm(self, context: str, selected_criteria: List[str], test_mode: bool = False) -> List[Dict[str, Any]]:
        """
        Génère des QCM basés sur des critères spécifiques
        
        Args:
            context (str): Contexte pour la génération
            selected_criteria (List[str]): Liste des critères sélectionnés
            test_mode (bool): Si True, génère seulement 1 QCM par critère
            
        Returns:
            List[Dict[str, Any]]: Liste des QCM générés
        """
        qcm_list = []
        
        # Filtrer les critères disponibles selon la sélection
        filtered_criteria = {k: v for k, v in self.criteria.items() if k in selected_criteria}
        
        if not filtered_criteria:
            logger.warning("No valid criteria selected. Returning empty list.")
            return []
            
        logger.info(f"Generating QCMs for selected criteria: {selected_criteria}")
        
        for criterion, details in filtered_criteria.items():
            # En mode test, on prend juste le premier type et niveau de difficulté
            # En mode normal, on parcourt tous les types et niveaux de difficulté
            types_to_use = details["types"][:1] if test_mode else details["types"]
            difficulties_to_use = details["difficulty_levels"][:1] if test_mode else details["difficulty_levels"]
            
            logger.info(f"For criterion {criterion}: Using {len(types_to_use)} types and {len(difficulties_to_use)} difficulty levels")
            
            for type_category in types_to_use:
                for difficulty in difficulties_to_use:
                    logger.info(f"Generating QCM for {criterion}/{type_category}/{difficulty}")
                    
                    prompt = self._create_criteria_prompt(context, criterion, type_category, difficulty)
                    
                    for attempt in range(RETRY_CONFIG["max_retries"]):
                        try:
                            response = self.invoke_model(prompt)
                            cleaned_response = self._clean_response(response)
                            
                            if not (cleaned_response.startswith('{') and cleaned_response.endswith('}')):
                                raise ValueError("Invalid response: not a valid JSON")
                            
                            qcm_data = json.loads(cleaned_response)
                            
                            # Validation de la structure du QCM
                            self._validate_qcm_structure(qcm_data)
                            
                            # Ajout des métadonnées de critère
                            qcm_data.update({
                                'criterion': criterion,
                                'type': type_category,
                                'difficulty': difficulty
                            })
                            
                            qcm_list.append(qcm_data)
                            logger.info(f"QCM generated successfully for {criterion}/{type_category}/{difficulty}")
                            
                            # Pause entre les générations pour respecter les limites de taux
                            time.sleep(RETRY_CONFIG["base_delay"])
                            break
                            
                        except Exception as e:
                            delay = RETRY_CONFIG["base_delay"] * (2 ** attempt)
                            if attempt < RETRY_CONFIG["max_retries"] - 1:
                                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
                                time.sleep(delay)
                            else:
                                logger.error(f"Failed to generate QCM after {RETRY_CONFIG['max_retries']} attempts: {str(e)}")
                                
                                # Ajouter un QCM d'erreur pour maintenir la structure
                                fake_qcm = {
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
                                qcm_list.append(fake_qcm)
                                logger.warning(f"QCM d'erreur ajouté pour {criterion}/{type_category}/{difficulty}")
            
        logger.info(f"Génération terminée: {len(qcm_list)} QCM générés pour les critères sélectionnés")
        return qcm_list

    def generate_qcm(self, context: str, selected_criteria: List[str] = None, test_mode: bool = False, num_generic_questions: int = 30) -> List[Dict[str, Any]]:
        """
        Génère des QCM basés sur le contexte fourni, avec ou sans critères spécifiques
        
        Args:
            context (str): Contexte pour la génération des QCM
            selected_criteria (List[str]): Critères sélectionnés pour la génération (None = générique)
            test_mode (bool): Si True, génère un nombre réduit de QCM
            num_generic_questions (int): Nombre de questions génériques à générer
            
        Returns:
            List[Dict[str, Any]]: Liste des QCM générés
        """
        if not selected_criteria:
            # Mode générique - nombre réduit en mode test
            num_to_generate = 5 if test_mode else num_generic_questions
            return self.generate_generic_qcm(context, num_to_generate)
        else:
            # Mode critères spécifiques
            return self.generate_criteria_qcm(context, selected_criteria, test_mode)
        


    def generate_single_generic_qcm(self, context: str) -> Dict[str, Any]:
        """Génère un seul QCM générique"""
        prompt = self.generic_prompt_template.format(context=context)
        
        for attempt in range(RETRY_CONFIG["max_retries"]):
            try:
                response = self.invoke_model(prompt)
                cleaned_response = self._clean_response(response)
                
                qcm_data = json.loads(cleaned_response)
                self._validate_qcm_structure(qcm_data)
                
                # Ajout des métadonnées génériques
                qcm_data.update({
                    'criterion': "Generic",
                    'type': "standard",
                    'difficulty': "medium"
                })
                
                return qcm_data
                
            except Exception as e:
                if attempt < RETRY_CONFIG["max_retries"] - 1:
                    time.sleep(RETRY_CONFIG["base_delay"] * (2 ** attempt))
                else:
                    logger.error(f"Failed to generate generic QCM: {str(e)}")
                    return {
                        'question': "Échec de génération d'un QCM générique",
                        'choices': {
                            'A': "Option A",
                            'B': "Option B", 
                            'C': "Option C",
                            'D': "Option D"
                        },
                        'correct_answer': 'A',
                        'points': 5,
                        'explanation': "QCM factice créé suite à une erreur de génération",
                        'criterion': "Generic",
                        'type': "standard",
                        'difficulty': "medium",
                        'is_fake': True
                    }
        
        return None

    def generate_specific_qcm(self, context: str, criterion: str, type_category: str, difficulty: str) -> Dict[str, Any]:
        """Génère un QCM pour un critère spécifique"""
        prompt = self._create_criteria_prompt(context, criterion, type_category, difficulty)
        
        for attempt in range(RETRY_CONFIG["max_retries"]):
            try:
                response = self.invoke_model(prompt)
                cleaned_response = self._clean_response(response)
                
                qcm_data = json.loads(cleaned_response)
                self._validate_qcm_structure(qcm_data)
                
                # Ajout des métadonnées de critère
                qcm_data.update({
                    'criterion': criterion,
                    'type': type_category,
                    'difficulty': difficulty
                })
                
                return qcm_data
                
            except Exception as e:
                if attempt < RETRY_CONFIG["max_retries"] - 1:
                    time.sleep(RETRY_CONFIG["base_delay"] * (2 ** attempt))
                else:
                    logger.error(f"Failed to generate specific QCM: {str(e)}")
                    return {
                        'question': f"Échec de génération d'un QCM pour {criterion}",
                        'choices': {
                            'A': "Option A",
                            'B': "Option B", 
                            'C': "Option C",
                            'D': "Option D"
                        },
                        'correct_answer': 'A',
                        'points': 5,
                        'explanation': f"QCM factice créé suite à une erreur de génération pour {criterion}/{type_category}/{difficulty}",
                        'criterion': criterion,
                        'type': type_category,
                        'difficulty': difficulty,
                        'is_fake': True
                    }
        
        return None

    def _validate_qcm_structure(self, qcm_data: Dict) -> None:
        """Valide la structure d'un QCM"""
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