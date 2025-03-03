class LLMEvaluationError(Exception):
    """Exception de base pour les erreurs liées à l'évaluation des LLM"""
    pass

class DocumentProcessingError(LLMEvaluationError):
    """Exception levée lors d'erreurs de traitement de documents"""
    pass

class EmbeddingError(LLMEvaluationError):
    """Exception levée lors d'erreurs de génération ou stockage d'embeddings"""
    pass

class QCMGenerationError(LLMEvaluationError):
    """Exception levée lors d'erreurs de génération de QCM"""
    pass

class ModelEvaluationError(LLMEvaluationError):
    """Exception levée lors d'erreurs d'évaluation du modèle"""
    pass

class APIError(LLMEvaluationError):
    """Exception levée lors d'erreurs d'API (Gemini, etc.)"""
    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)

class DatabaseError(LLMEvaluationError):
    """Exception levée lors d'erreurs de base de données"""
    pass

class ValidationError(LLMEvaluationError):
    """Exception levée lors d'erreurs de validation des données"""
    pass

class RateLimitError(APIError):
    """Exception levée lors du dépassement des limites d'API"""
    pass

class ConfigurationError(LLMEvaluationError):
    """Exception levée lors d'erreurs de configuration"""
    pass

class ReportGenerationError(LLMEvaluationError):
    """Exception levée lors d'erreurs de configuration"""
    pass