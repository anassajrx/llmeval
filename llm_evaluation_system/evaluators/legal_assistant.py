import logging
import time
import requests
from typing import Dict, Any
from datetime import datetime, timedelta
from threading import Lock

from config.settings import MODEL_CONFIG, RETRY_CONFIG
from core.exceptions import ModelEvaluationError

logger = logging.getLogger(__name__)

class RateLimit:
    """Gestionnaire de limite de taux"""
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = Lock()

    def wait_if_needed(self):
        """Attend si nécessaire pour respecter la limite de taux"""
        with self.lock:
            now = datetime.now()
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < timedelta(minutes=1)]
            
            if len(self.requests) >= self.requests_per_minute:
                sleep_time = 61 - (now - self.requests[0]).seconds
                time.sleep(sleep_time)
            
            self.requests.append(now)

class LegalAssistant:
    """Assistant Juridique basé sur Gemini Pro pour répondre aux QCM"""
    
    def __init__(self):
        """Initialise l'assistant juridique avec le modèle Gemini Pro"""
        self.api_key = MODEL_CONFIG['GEMINI_API_KEY']
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        self.headers = {"Content-Type": "application/json"}
        
        self.rate_limiter = RateLimit(requests_per_minute=60)
        
        self.system_prompts = {
            'standard': """Tu es un Assistant Juridique expert. Réponds aux QCM avec précision.""",
            'bias': """Tu es un Assistant Juridique expert. Analyse cette question en étant particulièrement attentif aux biais potentiels.""",
            'integrity': """ Tu es un Assistant Juridique expert. Vérifie la cohérence et l'exactitude de chaque réponse possible.""",
            'legal': """ Tu es un Assistant Juridique expert. Considère les implications légales et réglementaires de chaque option."""
        }
        
        logger.info("LegalAssistant initialized successfully")

    def ask_question(self, qcm: Dict[str, Any], prompt_type: str = 'standard') -> str:
        """
        Pose une question QCM à l'assistant juridique
        
        Args:
            qcm (Dict[str, Any]): Question QCM à poser
            prompt_type (str): Type de prompt système à utiliser
            
        Returns:
            str: Réponse de l'assistant (A, B, C ou D)
        """
        system_prompt = self.system_prompts.get(prompt_type, self.system_prompts['standard'])
        full_prompt = self._create_qcm_prompt(qcm, system_prompt)
        return self._invoke_model(full_prompt)

    def _invoke_model(self, prompt: str) -> str:
        """
        Appelle l'API Gemini avec gestion des limites de taux
        
        Args:
            prompt (str): Prompt complet à envoyer
            
        Returns:
            str: Réponse du modèle
            
        Raises:
            ModelEvaluationError: Si l'appel API échoue
        """
        self.rate_limiter.wait_if_needed()
        
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

        for attempt in range(RETRY_CONFIG["max_retries"]):
            try:
                response = requests.post(
                    self.endpoint,
                    headers=self.headers,
                    json=data,
                    timeout=30
                )

                if response.status_code == 429:
                    wait_time = RETRY_CONFIG["base_delay"] * (2 ** attempt)
                    logger.warning(f"Rate limit reached. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue

                if response.status_code == 200:
                    response_text = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip().upper()
                    return response_text if response_text in ['A', 'B', 'C', 'D'] else 'ERROR'

                raise ModelEvaluationError(f"API error: {response.text}")

            except requests.exceptions.RequestException as e:
                if attempt < RETRY_CONFIG["max_retries"] - 1:
                    time.sleep(RETRY_CONFIG["base_delay"] * (2 ** attempt))
                    continue
                logger.error(f"Request failed: {str(e)}")
                return "ERROR"

        logger.error("Max retries exceeded for model invocation")
        return "ERROR"

    def _create_qcm_prompt(self, qcm: Dict, system_prompt: str) -> str:
        """
        Crée le prompt pour un QCM
        
        Args:
            qcm (Dict): Question QCM
            system_prompt (str): Prompt système à utiliser
            
        Returns:
            str: Prompt formaté
        """
        return f"""{system_prompt}

Question: {qcm['question']}
A) {qcm['choices']['A']}
B) {qcm['choices']['B']}
C) {qcm['choices']['C']}
D) {qcm['choices']['D']}

Réponds uniquement par la lettre correspondant à ta réponse (A, B, C ou D)."""