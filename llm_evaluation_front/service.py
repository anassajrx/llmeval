import os
import sys
import logging
import asyncio
import uuid
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import shutil
from fastapi import UploadFile

# Ajout du chemin du backend au sys.path
backend_path = Path(r"C:\Users\ABENGMAH\OneDrive - Deloitte (O365D)\Desktop\Projects\new_workspace\llm_evaluation_system")
sys.path.append(str(backend_path))

# Import du système d'évaluation
from main import LLMEvaluationSystem
from config.settings import INPUT_DIR, OUTPUT_DIR
from utils.helpers import save_json, load_json

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm_evaluation_service")

class LLMEvaluationService:
    """Service d'interface entre l'API et le système d'évaluation LLM"""
    
    def __init__(self):
        """Initialise le service avec le système d'évaluation LLM"""
        self.evaluation_system = LLMEvaluationSystem()
        self.documents_dir = INPUT_DIR
        self.output_dir = OUTPUT_DIR
        
        # Stockage en mémoire des évaluations en cours
        self.evaluations = {}
        self.qcm_cache = {}
        
        # Créer les répertoires nécessaires
        Path(self.documents_dir).mkdir(parents=True, exist_ok=True)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Répertoire pour les données frontend
        self.frontend_data_dir = Path("static/data")
        self.frontend_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Répertoire pour les rapports
        self.frontend_reports_dir = Path("static/reports")
        self.frontend_reports_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("LLM Evaluation Service initialized successfully")
    
    # Correction dans la méthode upload_document de la classe LLMEvaluationService

    async def upload_document(self, file: UploadFile) -> Dict[str, Any]:
        """
        Charge un document sur le serveur et le déplace dans le répertoire d'entrée
        
        Args:
            file: Fichier uploadé
            
        Returns:
            Dict[str, Any]: Informations sur le document chargé
        """
        try:
            # Générer un ID unique
            doc_id = str(uuid.uuid4())
            
            # Récupérer l'extension du fichier original
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in ['.pdf', '.PDF']:
                return {"error": "Only PDF files are supported"}
            
            # Créer le chemin de destination
            dest_path = Path(self.documents_dir) / f"{doc_id}{file_ext}"
            
            # Copier le fichier vers le dossier d'entrée
            with open(dest_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Préparer les métadonnées du document
            doc_info = {
                "id": doc_id,
                "original_name": file.filename,
                "path": str(dest_path),
                "size": len(content),
                "upload_date": datetime.now().isoformat(),
                "status": "available"  # Mettre status à "available" immédiatement
            }
            
            # Sauvegarder les métadonnées du document
            doc_meta_path = self.frontend_data_dir / f"document_{doc_id}.json"
            with open(doc_meta_path, "w") as f:
                json.dump(doc_info, f)
            
            logger.info(f"Document uploaded successfully: {doc_id}")
            return doc_info
            
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise
    
    async def get_documents(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des documents disponibles
        
        Returns:
            List[Dict[str, Any]]: Liste des documents avec leurs métadonnées
        """
        try:
            documents = []
            
            # Chercher tous les fichiers de métadonnées de documents
            meta_files = list(self.frontend_data_dir.glob("document_*.json"))
            
            for meta_file in meta_files:
                try:
                    with open(meta_file, "r") as f:
                        doc_info = json.load(f)
                    
                    # Vérifier si le fichier existe toujours
                    if os.path.exists(doc_info["path"]):
                        documents.append(doc_info)
                    else:
                        # Mettre à jour le statut si le fichier n'existe plus
                        doc_info["status"] = "missing"
                        documents.append(doc_info)
                        with open(meta_file, "w") as f:
                            json.dump(doc_info, f)
                except Exception as e:
                    logger.error(f"Error reading document metadata {meta_file}: {str(e)}")
            
            # Trier les documents par date d'upload (du plus récent au plus ancien)
            documents.sort(key=lambda x: x["upload_date"], reverse=True)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            raise
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un document spécifique
        
        Args:
            document_id: ID du document
            
        Returns:
            Optional[Dict[str, Any]]: Informations sur le document ou None s'il n'existe pas
        """
        try:
            meta_path = self.frontend_data_dir / f"document_{document_id}.json"
            
            if not meta_path.exists():
                return None
                
            with open(meta_path, "r") as f:
                doc_info = json.load(f)
                
            # Vérifier si le fichier existe toujours
            if os.path.exists(doc_info["path"]):
                doc_info["status"] = "available"
            else:
                doc_info["status"] = "missing"
                
            return doc_info
            
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            raise
    
    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """
        Supprime un document
        
        Args:
            document_id: ID du document à supprimer
            
        Returns:
            Dict[str, Any]: Résultat de l'opération
        """
        try:
            meta_path = self.frontend_data_dir / f"document_{document_id}.json"
            
            if not meta_path.exists():
                return {"success": False, "error": "Document not found"}
                
            # Charger les métadonnées
            with open(meta_path, "r") as f:
                doc_info = json.load(f)
                
            # Supprimer le fichier s'il existe
            if os.path.exists(doc_info["path"]):
                os.remove(doc_info["path"])
                
            # Supprimer le fichier de métadonnées
            os.remove(meta_path)
            
            return {"success": True, "message": f"Document {document_id} deleted successfully"}
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            raise
    
    async def start_evaluation(self, document_ids: List[str], test_mode: bool = False) -> str:
        """
        Démarre une nouvelle évaluation
        
        Args:
            document_ids: Liste des IDs de documents à évaluer
            test_mode: Si True, exécute l'évaluation en mode test
            
        Returns:
            str: ID de l'évaluation
        """
        try:
            # Générer un ID unique pour l'évaluation
            evaluation_id = str(uuid.uuid4())
            
            # Récupérer les chemins des documents
            documents = []
            for doc_id in document_ids:
                doc_info = await self.get_document(doc_id)
                if doc_info and doc_info["status"] == "available":
                    documents.append(doc_info["path"])
            
            if not documents:
                raise ValueError("No valid documents found for evaluation")
            
            # Créer un enregistrement pour l'évaluation
            evaluation_info = {
                "id": evaluation_id,
                "documents": document_ids,
                "document_paths": documents,
                "test_mode": test_mode,
                "status": "pending",
                "progress": 0.0,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "total_qcm": 0,
                "completed_qcm": 0,
                "qcm_list": []
            }
            
            # Sauvegarder les métadonnées de l'évaluation
            self.evaluations[evaluation_id] = evaluation_info
            
            # Sauvegarder dans un fichier
            eval_meta_path = self.frontend_data_dir / f"evaluation_{evaluation_id}.json"
            with open(eval_meta_path, "w") as f:
                # Copier les données sans les chemins complets pour la sécurité
                safe_eval_info = evaluation_info.copy()
                safe_eval_info.pop("document_paths")
                json.dump(safe_eval_info, f)
            
            logger.info(f"Evaluation {evaluation_id} started for documents: {document_ids}")
            return evaluation_id
            
        except Exception as e:
            logger.error(f"Error starting evaluation: {str(e)}")
            raise
    
    async def run_evaluation_task(self, evaluation_id: str, document_ids: List[str], 
                                 test_mode: bool, manager) -> None:
        """
        Exécute l'évaluation en arrière-plan et met à jour le statut
        
        Args:
            evaluation_id: ID de l'évaluation
            document_ids: Liste des IDs de documents
            test_mode: Mode de test
            manager: Gestionnaire de connexions WebSocket
        """
        try:
            # Mettre à jour le statut
            self.evaluations[evaluation_id]["status"] = "running"
            await self._update_evaluation_status(evaluation_id, manager)
            
            # Récupérer les chemins des documents
            document_paths = self.evaluations[evaluation_id]["document_paths"]
            
            # Traiter les documents
            chunks = self.evaluation_system.process_documents(document_paths)
            
            # Générer et stocker les embeddings
            self.evaluation_system.generate_and_store_embeddings(chunks)
            
            # Générer les QCM (avec notifications pour les mises à jour)
            qcm_list = await self._generate_qcm_with_updates(evaluation_id, chunks[0], test_mode, manager)
            
            # Évaluer le modèle
            evaluation_results = self.evaluation_system.evaluate_model(qcm_list)
            
            # Générer les rapports
            report_paths = self.evaluation_system.generate_reports(evaluation_results)
            
            # Copier les rapports dans le répertoire frontend
            for report_type, report_path in report_paths.items():
                dest_path = self.frontend_reports_dir / f"{evaluation_id}_{report_type}.html"
                shutil.copy(report_path, dest_path)
            
            # Mettre à jour le statut final
            self.evaluations[evaluation_id]["status"] = "completed"
            self.evaluations[evaluation_id]["end_time"] = datetime.now().isoformat()
            self.evaluations[evaluation_id]["progress"] = 100.0
            self.evaluations[evaluation_id]["report_paths"] = {
                k: str(self.frontend_reports_dir / f"{evaluation_id}_{k}.html")
                for k in report_paths.keys()
            }
            self.evaluations[evaluation_id]["results"] = evaluation_results
            
            # Sauvegarder les métadonnées finales
            await self._save_evaluation_metadata(evaluation_id)
            
            # Notification finale
            await manager.broadcast({
                "type": "evaluation_completed",
                "evaluation_id": evaluation_id,
                "timestamp": datetime.now().isoformat()
            }, "notifications")
            
        except Exception as e:
            # Gérer les erreurs
            logger.error(f"Error running evaluation {evaluation_id}: {str(e)}")
            
            # Mettre à jour le statut en cas d'erreur
            if evaluation_id in self.evaluations:
                self.evaluations[evaluation_id]["status"] = "failed"
                self.evaluations[evaluation_id]["error"] = str(e)
                self.evaluations[evaluation_id]["end_time"] = datetime.now().isoformat()
                
                # Sauvegarder les métadonnées
                await self._save_evaluation_metadata(evaluation_id)
                
                # Notification d'erreur
                await manager.broadcast({
                    "type": "evaluation_error",
                    "evaluation_id": evaluation_id,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }, "notifications")
    
    async def _update_evaluation_status(self, evaluation_id: str, manager) -> None:
        """
        Met à jour le statut de l'évaluation via WebSocket
        
        Args:
            evaluation_id: ID de l'évaluation
            manager: Gestionnaire de connexions WebSocket
        """
        if evaluation_id in self.evaluations:
            eval_info = self.evaluations[evaluation_id]
            status_update = {
                "type": "evaluation_status",
                "evaluation_id": evaluation_id,
                "status": eval_info["status"],
                "progress": eval_info["progress"],
                "total_qcm": eval_info["total_qcm"],
                "completed_qcm": eval_info["completed_qcm"],
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast(status_update, "evaluation_status")
    
    async def _save_evaluation_metadata(self, evaluation_id: str) -> None:
        """
        Sauvegarde les métadonnées d'une évaluation
        
        Args:
            evaluation_id: ID de l'évaluation
        """
        if evaluation_id in self.evaluations:
            eval_meta_path = self.frontend_data_dir / f"evaluation_{evaluation_id}.json"
            safe_eval_info = self.evaluations[evaluation_id].copy()
            
            # Supprimer les chemins complets pour la sécurité
            if "document_paths" in safe_eval_info:
                safe_eval_info.pop("document_paths")
            
            with open(eval_meta_path, "w") as f:
                json.dump(safe_eval_info, f)
                
            logger.info(f"Saved evaluation metadata for {evaluation_id}")
    
    async def _generate_qcm_with_updates(self, evaluation_id: str, context: str, 
                                       test_mode: bool, manager) -> List[Dict[str, Any]]:
        """
        Génère les QCM avec des mises à jour en temps réel via WebSocket
        
        Args:
            evaluation_id: ID de l'évaluation
            context: Contexte pour la génération des QCM
            test_mode: Mode de test
            manager: Gestionnaire de connexions WebSocket
            
        Returns:
            List[Dict[str, Any]]: Liste des QCM générés
        """
        try:
            # Initialiser la liste des QCM
            qcm_list = []
            
            # Estimer le nombre total de QCM qui seront générés
            total_qcm = 5 if test_mode else 25  # Estimation très simplifiée
            self.evaluations[evaluation_id]["total_qcm"] = total_qcm
            
            # Générer les QCM
            generated_qcm = self.evaluation_system.qcm_generator.generate_qcm(context, test_mode)
            
            # Traiter chaque QCM généré
            for idx, qcm in enumerate(generated_qcm):
                # Ajouter un ID unique au QCM
                qcm["id"] = str(uuid.uuid4())
                
                # Ajouter le QCM à la liste
                qcm_list.append(qcm)
                self.evaluations[evaluation_id]["qcm_list"].append(qcm)
                self.evaluations[evaluation_id]["completed_qcm"] += 1
                
                # Calculer la progression
                progress = ((idx + 1) / total_qcm) * 100
                self.evaluations[evaluation_id]["progress"] = min(progress, 99.0)  # Max 99% jusqu'à la fin
                
                # Envoyer la mise à jour QCM
                await manager.broadcast({
                    "type": "qcm_generated",
                    "evaluation_id": evaluation_id,
                    "qcm": qcm,
                    "timestamp": datetime.now().isoformat()
                }, "qcm_updates")
                
                # Mettre à jour le statut de l'évaluation
                await self._update_evaluation_status(evaluation_id, manager)
                
                # Attendre un court instant pour simuler le temps de génération
                # et permettre aux clients de voir la progression
                await asyncio.sleep(0.2)
                
            # Mettre à jour les métadonnées
            await self._save_evaluation_metadata(evaluation_id)
            
            return qcm_list
            
        except Exception as e:
            logger.error(f"Error generating QCM: {str(e)}")
            raise
    
    async def get_evaluations(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des évaluations existantes
        
        Returns:
            List[Dict[str, Any]]: Liste des évaluations
        """
        try:
            evaluations = []
            
            # Chercher tous les fichiers de métadonnées d'évaluations
            meta_files = list(self.frontend_data_dir.glob("evaluation_*.json"))
            
            for meta_file in meta_files:
                try:
                    with open(meta_file, "r") as f:
                        evaluation_info = json.load(f)
                    
                    # Exclure la liste des QCM pour alléger les données
                    if "qcm_list" in evaluation_info:
                        evaluation_info.pop("qcm_list")
                    
                    evaluations.append(evaluation_info)
                except Exception as e:
                    logger.error(f"Error reading evaluation metadata {meta_file}: {str(e)}")
            
            # Trier les évaluations par date de début (du plus récent au plus ancien)
            evaluations.sort(key=lambda x: x.get("start_time", ""), reverse=True)
            
            return evaluations
            
        except Exception as e:
            logger.error(f"Error getting evaluations: {str(e)}")
            raise
    
    async def get_evaluation(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'une évaluation spécifique
        
        Args:
            evaluation_id: ID de l'évaluation
            
        Returns:
            Optional[Dict[str, Any]]: Informations sur l'évaluation ou None si elle n'existe pas
        """
        try:
            # D'abord vérifier si l'évaluation est en mémoire (en cours)
            if evaluation_id in self.evaluations:
                # Retourner une copie pour éviter la modification des données en mémoire
                return self.evaluations[evaluation_id].copy()
            
            # Sinon, chercher dans les fichiers
            meta_path = self.frontend_data_dir / f"evaluation_{evaluation_id}.json"
            
            if not meta_path.exists():
                return None
                
            with open(meta_path, "r") as f:
                evaluation_info = json.load(f)
                
            return evaluation_info
            
        except Exception as e:
            logger.error(f"Error getting evaluation {evaluation_id}: {str(e)}")
            raise
    
    async def get_evaluation_qcm(self, evaluation_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Récupère la liste des QCM d'une évaluation
        
        Args:
            evaluation_id: ID de l'évaluation
            
        Returns:
            Optional[List[Dict[str, Any]]]: Liste des QCM ou None si non trouvée
        """
        try:
            # D'abord vérifier si l'évaluation est en mémoire (en cours)
            if evaluation_id in self.evaluations:
                return self.evaluations[evaluation_id]["qcm_list"]
            
            # Sinon, chercher dans les fichiers
            meta_path = self.frontend_data_dir / f"evaluation_{evaluation_id}.json"
            
            if not meta_path.exists():
                return None
                
            with open(meta_path, "r") as f:
                evaluation_info = json.load(f)
                
            return evaluation_info.get("qcm_list", [])
            
        except Exception as e:
            logger.error(f"Error getting QCM for evaluation {evaluation_id}: {str(e)}")
            raise
    
    async def get_reports(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des rapports disponibles
        
        Returns:
            List[Dict[str, Any]]: Liste des rapports
        """
        try:
            reports = []
            
            # Chercher tous les fichiers de rapports
            report_files = list(self.frontend_reports_dir.glob("*_html.html"))
            
            # Regrouper les rapports par ID d'évaluation
            report_groups = {}
            for report_file in report_files:
                try:
                    file_name = report_file.name
                    eval_id = file_name.split("_")[0]
                    report_type = file_name.split("_")[1].split(".")[0]
                    
                    if eval_id not in report_groups:
                        report_groups[eval_id] = {
                            "id": str(uuid.uuid4()),
                            "evaluation_id": eval_id,
                            "creation_date": datetime.fromtimestamp(report_file.stat().st_mtime).isoformat(),
                            "report_files": {}
                        }
                    
                    report_groups[eval_id]["report_files"][report_type] = str(report_file)
                except Exception as e:
                    logger.error(f"Error processing report file {report_file}: {str(e)}")
            
            # Convertir les groupes en liste
            for eval_id, report_data in report_groups.items():
                # Récupérer le score si disponible
                try:
                    eval_meta_path = self.frontend_data_dir / f"evaluation_{eval_id}.json"
                    if eval_meta_path.exists():
                        with open(eval_meta_path, "r") as f:
                            eval_info = json.load(f)
                            if "results" in eval_info and "total_score" in eval_info["results"]:
                                report_data["score"] = eval_info["results"]["total_score"]
                except Exception as e:
                    logger.error(f"Error retrieving score for report {eval_id}: {str(e)}")
                
                reports.append(report_data)
            
            # Trier les rapports par date (du plus récent au plus ancien)
            reports.sort(key=lambda x: x["creation_date"], reverse=True)
            
            return reports
            
        except Exception as e:
            logger.error(f"Error getting reports: {str(e)}")
            raise
    
    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations d'un rapport spécifique
        
        Args:
            report_id: ID du rapport
            
        Returns:
            Optional[Dict[str, Any]]: Informations sur le rapport ou None s'il n'existe pas
        """
        try:
            reports = await self.get_reports()
            
            # Chercher le rapport par ID
            for report in reports:
                if report["id"] == report_id:
                    # Récupérer le contenu HTML du rapport principal
                    html_report_path = report["report_files"].get("html")
                    if html_report_path and os.path.exists(html_report_path):
                        with open(html_report_path, "r", encoding="utf-8") as f:
                            report["content"] = f.read()
                    
                    # Récupérer les données JSON du rapport si disponibles
                    json_report_path = report["report_files"].get("json")
                    if json_report_path and os.path.exists(json_report_path):
                        with open(json_report_path, "r", encoding="utf-8") as f:
                            report["data"] = json.load(f)
                    
                    return report
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {str(e)}")
            raise
    
    async def download_report(self, report_id: str, format: str = "html") -> Optional[str]:
        """
        Prépare un rapport pour le téléchargement
        
        Args:
            report_id: ID du rapport
            format: Format du rapport (html, pdf, csv, json)
            
        Returns:
            Optional[str]: Chemin du fichier à télécharger ou None s'il n'existe pas
        """
        try:
            reports = await self.get_reports()
            
            # Chercher le rapport par ID
            for report in reports:
                if report["id"] == report_id:
                    # Récupérer le fichier selon le format demandé
                    report_path = report["report_files"].get(format)
                    if report_path and os.path.exists(report_path):
                        return report_path
                    
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error downloading report {report_id}: {str(e)}")
            raise
    
    async def get_llm_info(self) -> Dict[str, Any]:
        """
        Récupère les informations sur le LLM utilisé
        
        Returns:
            Dict[str, Any]: Informations sur le LLM
        """
        try:
            # Ces informations seraient normalement extraites du backend
            # Pour l'instant, nous retournons des valeurs statiques
            return {
                "model": "Gemini Pro",
                "version": "2.0-flash",
                "role": "Assistant Juridique",
                "temperature": 0,
                "max_tokens": 2048,
                "description": "Modèle de langage optimisé pour l'évaluation des connaissances juridiques"
            }
            
        except Exception as e:
            logger.error(f"Error getting LLM info: {str(e)}")
            raise
    
    async def get_llm_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques de performance du LLM
        
        Returns:
            Dict[str, Any]: Statistiques de performance
        """
        try:
            # Récupérer toutes les évaluations
            evaluations = await self.get_evaluations()
            
            # Initialiser les statistiques
            stats = {
                "overall_score": 0,
                "success_rate": 0,
                "criteria_scores": {
                    "Bias": 0,
                    "Integrity": 0,
                    "Relevance": 0,
                    "Legal_Compliance": 0,
                    "Coherence": 0
                },
                "total_evaluations": 0,
                "total_qcm": 0,
                "success_examples": [],
                "failure_examples": []
            }
            
            # Calculer les statistiques à partir des évaluations complétées
            completed_evaluations = [e for e in evaluations if e.get("status") == "completed"]
            stats["total_evaluations"] = len(completed_evaluations)
            
            if not completed_evaluations:
                return stats
            
            # Agréger les résultats
            for eval_info in completed_evaluations:
                eval_id = eval_info["id"]
                evaluation = await self.get_evaluation(eval_id)
                
                if not evaluation or "results" not in evaluation:
                    continue
                
                results = evaluation["results"]
                
                # Agréger le score global
                stats["overall_score"] += results.get("total_score", 0)
                
                # Agréger le taux de succès
                stats["success_rate"] += results.get("success_rate", 0)
                
                # Agréger les scores par critère
                for criterion, criterion_stats in results.get("criteria_scores", {}).items():
                    if criterion in stats["criteria_scores"]:
                        stats["criteria_scores"][criterion] += criterion_stats.get("score", 0) / criterion_stats.get("total", 1) * 100
                
                # Compter le nombre total de QCM
                qcm_list = await self.get_evaluation_qcm(eval_id)
                stats["total_qcm"] += len(qcm_list) if qcm_list else 0
                
                # Collecter quelques exemples de succès et d'échec
                if len(stats["success_examples"]) < 3 and "details" in results:
                    success_examples = [d for d in results["details"] if d.get("score", 0) > 0]
                    if success_examples:
                        stats["success_examples"].append(success_examples[0])
                
                if len(stats["failure_examples"]) < 3 and "details" in results:
                    failure_examples = [d for d in results["details"] if d.get("score", 0) == 0]
                    if failure_examples:
                        stats["failure_examples"].append(failure_examples[0])
            
            # Calculer les moyennes
            if stats["total_evaluations"] > 0:
                stats["overall_score"] /= stats["total_evaluations"]
                stats["success_rate"] /= stats["total_evaluations"]
                
                for criterion in stats["criteria_scores"]:
                    stats["criteria_scores"][criterion] /= stats["total_evaluations"]
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting LLM statistics: {str(e)}")
            raise