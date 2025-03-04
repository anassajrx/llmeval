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
            await self._save_json_file(doc_meta_path, doc_info)
            
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
                    with open(meta_file, "r", encoding="utf-8") as f:
                        doc_info = json.load(f)
                    
                    # Vérifier si le fichier existe toujours
                    if os.path.exists(doc_info["path"]):
                        documents.append(doc_info)
                    else:
                        # Mettre à jour le statut si le fichier n'existe plus
                        doc_info["status"] = "missing"
                        documents.append(doc_info)
                        await self._save_json_file(meta_file, doc_info)
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
                
            with open(meta_path, "r", encoding="utf-8") as f:
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
            with open(meta_path, "r", encoding="utf-8") as f:
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
            await self._save_evaluation_metadata(evaluation_id)
            
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
            report_paths = await self.generate_reports(evaluation_id, evaluation_results)
            
            # Mettre à jour le statut final
            self.evaluations[evaluation_id]["status"] = "completed"
            self.evaluations[evaluation_id]["end_time"] = datetime.now().isoformat()
            self.evaluations[evaluation_id]["progress"] = 100.0
            self.evaluations[evaluation_id]["report_paths"] = report_paths
            self.evaluations[evaluation_id]["results"] = evaluation_results
            
            # Sauvegarder les métadonnées finales
            await self._save_evaluation_metadata(evaluation_id)
            
            # Notification finale avec gestion d'erreur
            try:
                await manager.broadcast({
                    "type": "evaluation_completed",
                    "evaluation_id": evaluation_id,
                    "timestamp": datetime.now().isoformat()
                }, "notifications")
            except Exception as e:
                logger.warning(f"Non-critical: Error broadcasting completion message: {str(e)}")
            
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
                
                # Notification d'erreur avec gestion d'erreur
                try:
                    await manager.broadcast({
                        "type": "evaluation_error",
                        "evaluation_id": evaluation_id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }, "notifications")
                except Exception as ex:
                    logger.warning(f"Non-critical: Error broadcasting error message: {str(ex)}")
    
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
            
            try:
                await manager.broadcast(status_update, "evaluation_status")
            except Exception as e:
                logger.warning(f"Non-critical: Error updating evaluation status: {str(e)}")
    
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
            
            await self._save_json_file(eval_meta_path, safe_eval_info)
            
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
                try:
                    await manager.broadcast({
                        "type": "qcm_generated",
                        "evaluation_id": evaluation_id,
                        "qcm": qcm,
                        "timestamp": datetime.now().isoformat()
                    }, "qcm_updates")
                except Exception as e:
                    logger.warning(f"Non-critical: Error broadcasting QCM update: {str(e)}")
                
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
                    with open(meta_file, "r", encoding="utf-8") as f:
                        evaluation_info = json.load(f)
                    
                    # Exclure la liste des QCM pour alléger les données
                    if "qcm_list" in evaluation_info:
                        evaluation_info["qcm_count"] = len(evaluation_info["qcm_list"])
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
                
            with open(meta_path, "r", encoding="utf-8") as f:
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
                
            with open(meta_path, "r", encoding="utf-8") as f:
                evaluation_info = json.load(f)
                
            return evaluation_info.get("qcm_list", [])
            
        except Exception as e:
            logger.error(f"Error getting QCM for evaluation {evaluation_id}: {str(e)}")
            raise
    
    async def generate_reports(self, evaluation_id: str, evaluation_results: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Génère les rapports pour une évaluation
        
        Args:
            evaluation_id: ID de l'évaluation
            evaluation_results: Résultats de l'évaluation (optionnel)
            
        Returns:
            Dict[str, str]: Chemins des rapports générés
        """
        try:
            # Si les résultats ne sont pas fournis, récupérer l'évaluation
            if evaluation_results is None:
                evaluation = await self.get_evaluation(evaluation_id)
                if not evaluation:
                    raise ValueError(f"Evaluation {evaluation_id} not found")
                evaluation_results = evaluation.get("results", {})
            else:
                evaluation = await self.get_evaluation(evaluation_id)
                if not evaluation:
                    raise ValueError(f"Evaluation {evaluation_id} not found")
            
            # Structure pour stocker les chemins des rapports
            report_paths = {}
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Créer un ID unique pour ce groupe de rapports
            report_group_id = str(uuid.uuid4())
            
            # Informations sur les documents liés à cette évaluation
            eval_documents = []
            for doc_id in evaluation.get("documents", []):
                doc_info = await self.get_document(doc_id)
                if doc_info:
                    eval_documents.append({
                        "id": doc_id,
                        "name": doc_info.get("original_name", "Unknown")
                    })
            
            # Générer le rapport HTML
            html_path = self.frontend_reports_dir / f"report_{evaluation_id}_{timestamp}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self._generate_html_report(evaluation, evaluation_results))
            report_paths["html"] = str(html_path)
            
            # Générer le rapport JSON
            json_path = self.frontend_reports_dir / f"report_{evaluation_id}_{timestamp}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "evaluation": evaluation,
                    "results": evaluation_results
                }, f, ensure_ascii=False, indent=4, sort_keys=True)
            report_paths["json"] = str(json_path)
            
            # Générer le rapport CSV avec les QCM
            csv_path = self.frontend_reports_dir / f"report_{evaluation_id}_{timestamp}.csv"
            self._generate_csv_report(evaluation, evaluation_results, csv_path)
            report_paths["csv"] = str(csv_path)
            
            # Enregistrer les métadonnées du rapport
            report_meta = {
                "id": report_group_id,
                "evaluation_id": evaluation_id,
                "creation_date": datetime.now().isoformat(),
                "report_files": report_paths,
                "document_ids": evaluation.get("documents", []),
                "documents": eval_documents,
                "total_qcm": evaluation.get("completed_qcm", 0),
                "score": evaluation_results.get("total_score", 0),
                "status": "completed"
            }
            
            # Sauvegarder les métadonnées du rapport
            report_meta_path = self.frontend_data_dir / f"report_{report_group_id}.json"
            await self._save_json_file(report_meta_path, report_meta)
            
            return report_paths
        except Exception as e:
            logger.error(f"Error generating reports: {str(e)}")
            raise
        
    def _generate_csv_report(self, evaluation: Dict, results: Dict, csv_path: Path) -> None:
        """
        Génère un rapport CSV avec les résultats des QCM
        
        Args:
            evaluation: Données de l'évaluation
            results: Résultats de l'évaluation
            csv_path: Chemin du fichier CSV à générer
        """
        import csv
        
        try:
            qcm_list = evaluation.get("qcm_list", [])
            details = results.get("details", [])
            
            # Créer un dictionnaire de résultats pour un accès facile
            results_dict = {}
            for detail in details:
                question = detail.get("question", "")
                results_dict[question] = detail
            
            with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                
                # Écrire l'en-tête
                writer.writerow([
                    "Critère", "Type", "Difficulté", "Question", 
                    "Réponse A", "Réponse B", "Réponse C", "Réponse D", 
                    "Réponse Correcte", "Réponse du Modèle", "Score"
                ])
                
                # Écrire les données pour chaque QCM
                for qcm in qcm_list:
                    question = qcm.get("question", "")
                    result = results_dict.get(question, {})
                    
                    row = [
                        qcm.get("criterion", ""),
                        qcm.get("type", ""),
                        qcm.get("difficulty", ""),
                        question,
                        qcm.get("choices", {}).get("A", ""),
                        qcm.get("choices", {}).get("B", ""),
                        qcm.get("choices", {}).get("C", ""),
                        qcm.get("choices", {}).get("D", ""),
                        qcm.get("correct_answer", ""),
                        result.get("model_answer", ""),
                        result.get("score", 0)
                    ]
                    
                    writer.writerow(row)
        except Exception as e:
            logger.error(f"Error generating CSV report: {str(e)}")
            # Créer un CSV minimal en cas d'erreur
            with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Error generating report", str(e)])
    
    def _generate_html_report(self, evaluation: Dict, results: Dict) -> str:
        """
        Génère le contenu HTML d'un rapport d'évaluation
        
        Args:
            evaluation: Données de l'évaluation
            results: Résultats de l'évaluation
            
        Returns:
            str: Contenu HTML
        """
        eval_id = evaluation.get("id", "")
        start_time = evaluation.get("start_time", "")
        end_time = evaluation.get("end_time", "")
        total_qcm = evaluation.get("completed_qcm", 0)
        
        total_score = results.get("total_score", 0)
        success_rate = results.get("success_rate", 0)
        criteria_scores = results.get("criteria_scores", {})
        
        # Construire une table pour les scores par critère
        criteria_table = ""
        for criterion, stats in criteria_scores.items():
            score_pct = (stats.get("score", 0) / stats.get("total", 1)) * 100 if stats.get("total", 0) > 0 else 0
            criteria_table += f"""
            <tr>
                <td>{criterion}</td>
                <td>{score_pct:.1f}%</td>
                <td>{stats.get("success_count", 0)}/{stats.get("questions_count", 0)}</td>
            </tr>
            """
        
        # Construire une table pour les QCM
        qcm_table = ""
        for detail in results.get("details", []):
            qcm_table += f"""
            <tr>
                <td>{detail.get("criterion", "")}</td>
                <td>{detail.get("question", "")}</td>
                <td>{detail.get("correct_answer", "")}</td>
                <td>{detail.get("model_answer", "")}</td>
                <td>{detail.get("score", 0)}/{detail.get("max_points", 0)}</td>
            </tr>
            """
        
        # Générer le rapport complet
        html = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rapport d'Évaluation LLM</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ margin: 20px 0; }}
                .summary-item {{ margin-bottom: 10px; }}
                .score {{font-weight: bold; color: #86bc24; }}
            </style>
        </head>
        <body>
            <h1>Rapport d'Évaluation LLM</h1>
            
            <div class="summary">
                <h2>Résumé</h2>
                <div class="summary-item"><strong>ID:</strong> {eval_id}</div>
                <div class="summary-item"><strong>Date de début:</strong> {start_time}</div>
                <div class="summary-item"><strong>Date de fin:</strong> {end_time}</div>
                <div class="summary-item"><strong>Total QCM:</strong> {total_qcm}</div>
                <div class="summary-item"><strong>Score global:</strong> <span class="score">{total_score:.1f}%</span></div>
                <div class="summary-item"><strong>Taux de succès:</strong> {success_rate:.1f}%</div>
            </div>
            
            <h2>Performance par Critère</h2>
            <table>
                <thead>
                    <tr>
                        <th>Critère</th>
                        <th>Score (%)</th>
                        <th>Succès/Total</th>
                    </tr>
                </thead>
                <tbody>
                    {criteria_table}
                </tbody>
            </table>
            
            <h2>Détails des QCM</h2>
            <table>
                <thead>
                    <tr>
                        <th>Critère</th>
                        <th>Question</th>
                        <th>Réponse Correcte</th>
                        <th>Réponse du Modèle</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    {qcm_table}
                </tbody>
            </table>
        </body>
        </html>
        """
        
        return html
    
    async def get_reports(self, evaluation_id: Optional[str] = None, 
                      document_id: Optional[str] = None,
                      date_from: Optional[str] = None, 
                      date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des rapports disponibles avec filtrage
        
        Args:
            evaluation_id: Filtrer par ID d'évaluation
            document_id: Filtrer par ID de document
            date_from: Filtrer par date à partir de (format ISO)
            date_to: Filtrer par date jusqu'à (format ISO)
            
        Returns:
            List[Dict[str, Any]]: Liste des rapports
        """
        try:
            reports = []
            
            # Chercher tous les fichiers de métadonnées de rapports
            meta_files = list(self.frontend_data_dir.glob("report_*.json"))
            
            for meta_file in meta_files:
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        report_data = json.load(f)
                    
                    # Appliquer les filtres
                    if evaluation_id and report_data.get("evaluation_id") != evaluation_id:
                        continue
                        
                    if document_id and document_id not in report_data.get("document_ids", []):
                        continue
                        
                    if date_from:
                        report_date = datetime.fromisoformat(report_data.get("creation_date", ""))
                        filter_date = datetime.fromisoformat(date_from)
                        if report_date < filter_date:
                            continue
                            
                    if date_to:
                        report_date = datetime.fromisoformat(report_data.get("creation_date", ""))
                        filter_date = datetime.fromisoformat(date_to)
                        if report_date > filter_date:
                            continue
                    
                    reports.append(report_data)
                except Exception as e:
                    logger.error(f"Error reading report metadata {meta_file}: {str(e)}")
            
            # Trier les rapports par date (du plus récent au plus ancien)
            reports.sort(key=lambda x: x.get("creation_date", ""), reverse=True)
            
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
            meta_path = self.frontend_data_dir / f"report_{report_id}.json"
            
            if not meta_path.exists():
                return None
                
            with open(meta_path, "r", encoding="utf-8") as f:
                report_info = json.load(f)
            
            # Récupérer le contenu des fichiers de rapport
            for format_type, file_path in report_info.get("report_files", {}).items():
                if os.path.exists(file_path):
                    if format_type == "html":
                        with open(file_path, "r", encoding="utf-8") as f:
                            report_info["content"] = f.read()
                    elif format_type == "json":
                        with open(file_path, "r", encoding="utf-8") as f:
                            report_info["data"] = json.load(f)
            
            return report_info
            
        except Exception as e:
            logger.error(f"Error getting report {report_id}: {str(e)}")
            raise
    
    async def download_report(self, report_id: str, format: str = "html") -> Optional[str]:
        """
        Prépare un rapport pour le téléchargement
        
        Args:
            report_id: ID du rapport
            format: Format du rapport (html, json, csv)
            
        Returns:
            Optional[str]: Chemin du fichier à télécharger ou None s'il n'existe pas
        """
        try:
            report_info = await self.get_report(report_id)
            
            if not report_info or "report_files" not in report_info:
                return None
            
            # Récupérer le chemin du fichier pour le format demandé
            file_path = report_info["report_files"].get(format)
            
            if not file_path or not os.path.exists(file_path):
                return None
            
            return file_path
            
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
    
    async def _save_json_file(self, file_path: Path, data: Dict) -> None:
        """
        Sauvegarde des données au format JSON de façon asynchrone
        
        Args:
            file_path: Chemin du fichier
            data: Données à sauvegarder
        """
        def write_json():
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=True)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_json)