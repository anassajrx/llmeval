import os
import sys
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from starlette.requests import Request
import json
import asyncio
from datetime import datetime
import shutil

# Ajout du chemin du backend au sys.path
backend_path = Path(r"C:\Users\ABENGMAH\OneDrive - Deloitte (O365D)\Desktop\Projects\new_workspace\llm_evaluation_system")
sys.path.append(str(backend_path))

# Import du service
from service import LLMEvaluationService

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("llm_evaluation_api")

# Modèles Pydantic
class EvaluationRequest(BaseModel):
    document_ids: List[str]
    test_mode: bool = False

# Classe pour gérer les WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "qcm_updates": [],
            "evaluation_status": [],
            "notifications": []
        }

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel in self.active_connections:
            self.active_connections[channel].append(websocket)
            logger.info(f"Client connected to {channel} channel")

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections and websocket in self.active_connections[channel]:
            self.active_connections[channel].remove(websocket)
            logger.info(f"Client disconnected from {channel} channel")

    async def broadcast(self, message: Dict[str, Any], channel: str):
        if channel not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[channel]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
                logger.info(f"Client disconnected from {channel} channel during broadcast")
            except Exception as e:
                logger.warning(f"Error sending WebSocket message: {str(e)}")
                disconnected.append(connection)
        
        # Nettoyer les connexions déconnectées
        for conn in disconnected:
            self.disconnect(conn, channel)

# Création de l'application FastAPI
app = FastAPI(title="LLM Evaluation System API", version="1.0.0")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation des services
manager = ConnectionManager()
service = LLMEvaluationService()

# Configuration des fichiers statiques et templates
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes pour les pages HTML
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/documents")
async def documents_page(request: Request):
    return templates.TemplateResponse("documents.html", {"request": request})

@app.get("/evaluations")
async def evaluations_page(request: Request):
    return templates.TemplateResponse("evaluations.html", {"request": request})

@app.get("/reports")
async def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})

@app.get("/llm-panel")
async def llm_panel_page(request: Request):
    return templates.TemplateResponse("llm_panel.html", {"request": request})

# API Routes - Documents
@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        result = await service.upload_document(file)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@app.get("/api/documents")
async def get_documents():
    try:
        documents = await service.get_documents()
        return JSONResponse(content={"documents": documents})
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve documents: {str(e)}")

@app.get("/api/documents/{document_id}")
async def get_document(document_id: str):
    try:
        document = await service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
        return JSONResponse(content=document)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    try:
        result = await service.delete_document(document_id)
        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=f"Document with ID {document_id} not found")
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

# API Routes - Évaluations
@app.post("/api/evaluations/start")
async def start_evaluation(request: EvaluationRequest, background_tasks: BackgroundTasks):
    try:
        evaluation_id = await service.start_evaluation(request.document_ids, request.test_mode)
        # Démarrer l'évaluation en arrière-plan
        background_tasks.add_task(service.run_evaluation_task, evaluation_id, request.document_ids, request.test_mode, manager)
        return JSONResponse(content={"evaluation_id": evaluation_id, "status": "started"})
    except Exception as e:
        logger.error(f"Error starting evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start evaluation: {str(e)}")

@app.get("/api/evaluations")
async def get_evaluations():
    try:
        evaluations = await service.get_evaluations()
        return JSONResponse(content={"evaluations": evaluations})
    except Exception as e:
        logger.error(f"Error getting evaluations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve evaluations: {str(e)}")

@app.get("/api/evaluations/{evaluation_id}")
async def get_evaluation(evaluation_id: str):
    try:
        evaluation = await service.get_evaluation(evaluation_id)
        if not evaluation:
            raise HTTPException(status_code=404, detail=f"Evaluation with ID {evaluation_id} not found")
        return JSONResponse(content=evaluation)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evaluation {evaluation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve evaluation: {str(e)}")

@app.get("/api/evaluations/{evaluation_id}/qcm")
async def get_evaluation_qcm(evaluation_id: str):
    try:
        qcm_list = await service.get_evaluation_qcm(evaluation_id)
        if qcm_list is None:
            raise HTTPException(status_code=404, detail=f"QCM list for evaluation {evaluation_id} not found")
        return JSONResponse(content={"qcm_list": qcm_list})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting QCM for evaluation {evaluation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve QCM list: {str(e)}")

# API Routes - Rapports
@app.get("/api/reports")
async def get_reports():
    try:
        reports = await service.get_reports()
        return JSONResponse(content={"reports": reports})
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve reports: {str(e)}")

@app.get("/api/reports/filter")
async def filter_reports(evaluation_id: Optional[str] = None, document_id: Optional[str] = None, 
                         date_from: Optional[str] = None, date_to: Optional[str] = None):
    try:
        reports = await service.get_reports(evaluation_id, document_id, date_from, date_to)
        return JSONResponse(content={"reports": reports})
    except Exception as e:
        logger.error(f"Error filtering reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to filter reports: {str(e)}")

@app.get("/api/reports/{report_id}")
async def get_report(report_id: str):
    try:
        report = await service.get_report(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        return JSONResponse(content=report)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve report: {str(e)}")

@app.get("/api/reports/download/{report_id}")
async def download_report(report_id: str, format: str = "html"):
    try:
        report_path = await service.download_report(report_id, format)
        if not report_path:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found or format {format} not available")
            
        # Créer un nom de fichier propre pour le téléchargement
        report = await service.get_report(report_id)
        evaluation_id = report.get("evaluation_id", "unknown")
        date_str = datetime.now().strftime("%Y%m%d")
        
        filename = f"LLM_Evaluation_Report_{evaluation_id}_{date_str}.{format}"
        
        return FileResponse(path=report_path, filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download report: {str(e)}")
    

# API Routes - LLM
@app.get("/api/llm/info")
async def get_llm_info():
    try:
        llm_info = await service.get_llm_info()
        return JSONResponse(content=llm_info)
    except Exception as e:
        logger.error(f"Error getting LLM info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve LLM info: {str(e)}")

@app.get("/api/llm/statistics")
async def get_llm_statistics():
    try:
        llm_stats = await service.get_llm_statistics()
        return JSONResponse(content=llm_stats)
    except Exception as e:
        logger.error(f"Error getting LLM statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve LLM statistics: {str(e)}")

# WebSocket routes
@app.websocket("/ws/qcm-updates")
async def websocket_qcm_updates(websocket: WebSocket):
    await manager.connect(websocket, "qcm_updates")
    try:
        while True:
            # Keep the connection open
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "qcm_updates")

@app.websocket("/ws/evaluation-status")
async def websocket_evaluation_status(websocket: WebSocket):
    await manager.connect(websocket, "evaluation_status")
    try:
        while True:
            # Keep the connection open
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "evaluation_status")

@app.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    await manager.connect(websocket, "notifications")
    try:
        while True:
            # Keep the connection open
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "notifications")

# Route pour la santé de l'API
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Exécution de l'application
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)