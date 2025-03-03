/**
 * Script pour la page des évaluations
 */

document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const newEvalBtnEl = document.getElementById('new-eval-btn');
    const evalStatusEl = document.getElementById('eval-status');
    const evalDetailsEl = document.getElementById('eval-details');
    const evalProgressEl = document.getElementById('eval-progress');
    const evalProgressTextEl = document.getElementById('eval-progress-text');
    const evalQcmCountEl = document.getElementById('eval-qcm-count');
    const qcmListEl = document.getElementById('qcm-list');
    const qcmEmptyEl = document.getElementById('qcm-empty');
    const evaluationsTableBodyEl = document.getElementById('evaluations-table-body');
    const documentSelectionEl = document.getElementById('document-selection');
    const testModeEl = document.getElementById('test-mode');
    
    // Initialiser les modals
    const newEvalModal = Utils.initModal('new-eval-modal');
    const evaluationDetailsModal = Utils.initModal('evaluation-details-modal');
    
    // Variables
    let currentEvaluationId = null;
    let selectedDocuments = [];
    
    // Charger les évaluations
    loadEvaluations();
    
    // Connecter aux WebSockets
    WebSocketManager.connect('qcm-updates', handleQcmUpdates);
    WebSocketManager.connect('evaluation-status', handleEvaluationStatus);
    
    // Vérifier si une évaluation est en cours
    checkActiveEvaluation();
    
    // Écouter les événements
    newEvalBtnEl.addEventListener('click', () => {
        showNewEvaluationModal();
    });
    
    document.getElementById('new-eval-form').addEventListener('submit', (e) => {
        e.preventDefault();
        startNewEvaluation();
    });
    
    /**
     * Charge la liste des évaluations
     */
    async function loadEvaluations() {
        try {
            const response = await fetch('/api/evaluations');
            const data = await response.json();
            
            renderEvaluationsList(data.evaluations || []);
        } catch (error) {
            console.error('Erreur lors du chargement des évaluations:', error);
            Utils.showToast('Erreur lors du chargement des évaluations', 'error');
        }
    }
    
    /**
     * Vérifie si une évaluation est actuellement en cours
     */
    async function checkActiveEvaluation() {
        try {
            const response = await fetch('/api/evaluations');
            const data = await response.json();
            
            const evaluations = data.evaluations || [];
            
            // Chercher une évaluation en cours ou en attente
            const activeEval = evaluations.find(eval => 
                eval.status === 'running' || eval.status === 'pending'
            );
            
            if (activeEval) {
                currentEvaluationId = activeEval.id;
                updateEvaluationStatus(activeEval);
                loadEvaluationQcms(activeEval.id);
            }
        } catch (error) {
            console.error('Erreur lors de la vérification d\'évaluation active:', error);
        }
    }
    
    /**
     * Affiche le modal pour démarrer une nouvelle évaluation
     */
    // Correction dans la fonction showNewEvaluationModal

async function showNewEvaluationModal() {
    try {
        // Réinitialiser la sélection des documents
        selectedDocuments = [];
        
        // Afficher le modal
        newEvalModal.open();
        
        // Charger les documents disponibles
        documentSelectionEl.innerHTML = '<div class="loading">Chargement des documents...</div>';
        
        const response = await fetch('/api/documents');
        const data = await response.json();
        
        const documents = data.documents || [];
        console.log("Documents récupérés:", documents);
        
        // Filtrer les documents disponibles
        const availableDocuments = documents.filter(doc => doc.status === 'available');
        console.log("Documents disponibles:", availableDocuments);
        
        if (availableDocuments.length === 0) {
            documentSelectionEl.innerHTML = '<div class="empty-state">Aucun document disponible</div>';
            return;
        }
        
        // Afficher les documents
        documentSelectionEl.innerHTML = '';
        availableDocuments.forEach(doc => {
            const docEl = document.createElement('div');
            docEl.className = 'document-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `doc-${doc.id}`;
            checkbox.value = doc.id;
            
            const label = document.createElement('label');
            label.htmlFor = `doc-${doc.id}`;
            label.textContent = doc.original_name;
            
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    selectedDocuments.push(doc.id);
                    console.log("Document ajouté:", doc.id);
                    console.log("Documents sélectionnés:", selectedDocuments);
                } else {
                    selectedDocuments = selectedDocuments.filter(id => id !== doc.id);
                    console.log("Document retiré:", doc.id);
                    console.log("Documents sélectionnés:", selectedDocuments);
                }
            });
            
            docEl.appendChild(checkbox);
            docEl.appendChild(label);
            documentSelectionEl.appendChild(docEl);
        });
        
    } catch (error) {
        console.error('Erreur lors du chargement des documents:', error);
        documentSelectionEl.innerHTML = '<div class="error">Erreur lors du chargement des documents</div>';
    }
}
    
    /**
     * Démarre une nouvelle évaluation
     */
    async function startNewEvaluation() {
        if (selectedDocuments.length === 0) {
            Utils.showToast('Veuillez sélectionner au moins un document', 'error');
            return;
        }
        
        try {
            const response = await fetch('/api/evaluations/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    document_ids: selectedDocuments,
                    test_mode: testModeEl.checked
                })
            });
            
            const result = await response.json();
            
            if (result.evaluation_id) {
                Utils.showToast('Évaluation démarrée avec succès', 'success');
                
                // Fermer le modal
                newEvalModal.close();
                
                // Réinitialiser la sélection
                selectedDocuments = [];
                
                // Définir l'évaluation courante
                currentEvaluationId = result.evaluation_id;
                
                // Mettre à jour l'interface
                updateCurrentEvaluation({
                    id: result.evaluation_id,
                    status: 'pending',
                    progress: 0,
                    total_qcm: 0,
                    completed_qcm: 0
                });
                
                // Vider la liste des QCM
                qcmListEl.innerHTML = '';
                qcmEmptyEl.style.display = 'block';
                
                // Rafraîchir la liste des évaluations
                setTimeout(loadEvaluations, 1000);
            } else {
                Utils.showToast('Erreur lors du démarrage de l\'évaluation', 'error');
            }
            
        } catch (error) {
            console.error('Erreur lors du démarrage de l\'évaluation:', error);
            Utils.showToast('Erreur lors du démarrage de l\'évaluation', 'error');
        }
    }
    
    /**
     * Affiche la liste des évaluations
     * @param {Array} evaluations - Liste des évaluations
     */
    function renderEvaluationsList(evaluations) {
        // Vider la table
        evaluationsTableBodyEl.innerHTML = '';
        
        if (evaluations.length === 0) {
            evaluationsTableBodyEl.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">Aucune évaluation disponible</td>
                </tr>
            `;
            return;
        }
        
        // Ajouter chaque évaluation
        evaluations.forEach(evaluation => {
            const row = document.createElement('tr');
            row.setAttribute('data-evaluation-id', evaluation.id);
            
            // ID court
            const idCell = document.createElement('td');
            idCell.textContent = evaluation.id.substring(0, 8) + '...';
            row.appendChild(idCell);
            
            // Date
            const dateCell = document.createElement('td');
            dateCell.textContent = Utils.formatDate(evaluation.start_time, true);
            row.appendChild(dateCell);
            
            // Documents
            const docsCell = document.createElement('td');
            docsCell.textContent = (evaluation.documents || []).length;
            row.appendChild(docsCell);
            
            // QCM
            const qcmCell = document.createElement('td');
            qcmCell.textContent = evaluation.completed_qcm || 0;
            row.appendChild(qcmCell);
            
            // Statut
            const statusCell = document.createElement('td');
            const statusEl = document.createElement('span');
            statusEl.className = `status-${evaluation.status}`;
            statusEl.textContent = evaluation.status;
            statusCell.appendChild(statusEl);
            row.appendChild(statusCell);
            
            // Actions
            const actionsCell = document.createElement('td');
            actionsCell.className = 'table-actions';
            
            // Bouton détails
            const viewBtn = document.createElement('button');
            viewBtn.className = 'action-btn view-btn';
            viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
            viewBtn.title = 'Voir les détails';
            viewBtn.addEventListener('click', () => showEvaluationDetails(evaluation.id));
            actionsCell.appendChild(viewBtn);
            
            row.appendChild(actionsCell);
            
            evaluationsTableBodyEl.appendChild(row);
        });
    }
    
    /**
     * Met à jour l'affichage de l'évaluation en cours
     * @param {Object} evaluation - Données de l'évaluation
     */
    function updateCurrentEvaluation(evaluation) {
        if (!evaluation) {
            evalStatusEl.textContent = 'Aucune';
            evalDetailsEl.textContent = '';
            evalProgressEl.style.width = '0%';
            evalProgressTextEl.textContent = '0%';
            evalQcmCountEl.textContent = '0/0 QCM';
            return;
        }
        
        evalStatusEl.textContent = evaluation.status;
        
        if (evaluation.status === 'running') {
            evalDetailsEl.textContent = 'Évaluation en cours...';
        } else if (evaluation.status === 'pending') {
            evalDetailsEl.textContent = 'En attente de démarrage...';
        } else if (evaluation.status === 'completed') {
            evalDetailsEl.textContent = `Terminée le ${Utils.formatDate(evaluation.end_time, true)}`;
        } else if (evaluation.status === 'failed') {
            evalDetailsEl.textContent = `Échec: ${evaluation.error || 'Erreur inconnue'}`;
        }
        
        const progress = evaluation.progress || 0;
        evalProgressEl.style.width = `${progress}%`;
        evalProgressTextEl.textContent = `${Math.round(progress)}%`;
        
        const totalQcm = evaluation.total_qcm || 0;
        const completedQcm = evaluation.completed_qcm || 0;
        evalQcmCountEl.textContent = `${completedQcm}/${totalQcm} QCM`;
    }
    
    /**
     * Charge les QCM d'une évaluation
     * @param {string} evaluationId - ID de l'évaluation
     */
    async function loadEvaluationQcms(evaluationId) {
        try {
            const response = await fetch(`/api/evaluations/${evaluationId}/qcm`);
            const data = await response.json();
            
            const qcmList = data.qcm_list || [];
            
            if (qcmList.length === 0) {
                qcmEmptyEl.style.display = 'block';
                return;
            }
            
            qcmEmptyEl.style.display = 'none';
            qcmListEl.innerHTML = '';
            
            // Afficher les QCM du plus récent au plus ancien
            [...qcmList].reverse().forEach(qcm => {
                const qcmEl = createQcmElement(qcm);
                qcmListEl.appendChild(qcmEl);
            });
            
        } catch (error) {
            console.error('Erreur lors du chargement des QCM:', error);
        }
    }
    
    /**
     * Crée un élément pour afficher un QCM
     * @param {Object} qcm - Données du QCM
     * @returns {HTMLElement} Élément QCM
     */
    function createQcmElement(qcm) {
        const qcmEl = document.createElement('div');
        qcmEl.className = 'qcm-card';
        qcmEl.setAttribute('data-qcm-id', qcm.id);
        
        const qcmHeader = document.createElement('div');
        qcmHeader.className = 'qcm-header';
        
        const qcmTitle = document.createElement('div');
        qcmTitle.className = 'qcm-title';
        qcmTitle.textContent = `QCM ${qcm.id.substring(0, 8)}`;
        
        const qcmMeta = document.createElement('div');
        qcmMeta.className = 'qcm-meta';
        
        const qcmCriterion = document.createElement('span');
        qcmCriterion.className = 'qcm-criterion';
        qcmCriterion.textContent = qcm.criterion;
        
        const qcmDifficulty = document.createElement('span');
        qcmDifficulty.textContent = `Difficulté: ${qcm.difficulty}`;
        
        qcmMeta.appendChild(qcmCriterion);
        qcmMeta.appendChild(qcmDifficulty);
        
        qcmHeader.appendChild(qcmTitle);
        qcmHeader.appendChild(qcmMeta);
        
        const qcmQuestion = document.createElement('div');
        qcmQuestion.className = 'qcm-question';
        qcmQuestion.textContent = qcm.question;
        
        const qcmChoices = document.createElement('div');
        qcmChoices.className = 'qcm-choices';
        
        for (const [letter, choice] of Object.entries(qcm.choices)) {
            const choiceEl = document.createElement('div');
            choiceEl.className = `qcm-choice ${letter === qcm.correct_answer ? 'correct' : ''}`;
            
            const letterSpan = document.createElement('span');
            letterSpan.className = 'choice-letter';
            letterSpan.textContent = letter;
            
            choiceEl.appendChild(letterSpan);
            choiceEl.appendChild(document.createTextNode(choice));
            
            qcmChoices.appendChild(choiceEl);
        }
        
        qcmEl.appendChild(qcmHeader);
        qcmEl.appendChild(qcmQuestion);
        qcmEl.appendChild(qcmChoices);
        
        return qcmEl;
    }
    
    /**
     * Affiche les détails d'une évaluation
     * @param {string} evaluationId - ID de l'évaluation
     */
    async function showEvaluationDetails(evaluationId) {
        try {
            // Afficher le modal avec un message de chargement
            evaluationDetailsModal.setContent('<div class="loading">Chargement des détails...</div>');
            evaluationDetailsModal.open();
            
            // Charger les détails de l'évaluation
            const response = await fetch(`/api/evaluations/${evaluationId}`);
            const evaluation = await response.json();
            
            // Créer le contenu du modal
            const content = evaluation ? createEvaluationDetailsContent(evaluation) : 
                '<div class="error">Évaluation non trouvée</div>';
            
            // Mettre à jour le contenu du modal
            evaluationDetailsModal.setContent(content);
            
        } catch (error) {
            console.error('Erreur lors du chargement des détails de l\'évaluation:', error);
            evaluationDetailsModal.setContent('<div class="error">Erreur lors du chargement des détails</div>');
        }
    }
    
    /**
     * Crée le contenu HTML pour les détails d'une évaluation
     * @param {Object} evaluation - Données de l'évaluation
     * @returns {string} Contenu HTML
     */
    function createEvaluationDetailsContent(evaluation) {
        const documentsText = evaluation.documents && evaluation.documents.length > 0 
            ? evaluation.documents.length + ' document(s)' 
            : 'Aucun document';
            
        const qcmText = evaluation.completed_qcm 
            ? `${evaluation.completed_qcm}/${evaluation.total_qcm} QCM` 
            : 'Aucun QCM';
            
        const startTime = Utils.formatDate(evaluation.start_time, true);
        const endTime = evaluation.end_time ? Utils.formatDate(evaluation.end_time, true) : 'En cours';
        
        const durationText = evaluation.end_time 
            ? calculateDuration(evaluation.start_time, evaluation.end_time)
            : 'En cours';
        
        return `
            <div class="evaluation-details">
                <div class="detail-item">
                    <div class="detail-label">ID:</div>
                    <div class="detail-value">${evaluation.id}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Statut:</div>
                    <div class="detail-value">
                        <span class="status-${evaluation.status}">
                            ${evaluation.status}
                        </span>
                    </div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Documents:</div>
                    <div class="detail-value">${documentsText}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">QCM:</div>
                    <div class="detail-value">${qcmText}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Démarré:</div>
                    <div class="detail-value">${startTime}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Terminé:</div>
                    <div class="detail-value">${endTime}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Durée:</div>
                    <div class="detail-value">${durationText}</div>
                </div>
                ${evaluation.error ? `
                <div class="detail-item">
                    <div class="detail-label">Erreur:</div>
                    <div class="detail-value error">${evaluation.error}</div>
                </div>
                ` : ''}
                ${evaluation.results ? `
                <div class="detail-item">
                    <div class="detail-label">Score total:</div>
                    <div class="detail-value">${evaluation.results.total_score.toFixed(1)}%</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Taux de succès:</div>
                    <div class="detail-value">${evaluation.results.success_rate.toFixed(1)}%</div>
                </div>
                ` : ''}
            </div>
            ${evaluation.report_paths ? `
            <div class="detail-actions">
                <h3>Rapports disponibles</h3>
                <div class="report-links">
                    ${Object.entries(evaluation.report_paths).map(([type, path]) => `
                        <a href="/reports?report=${type}&id=${evaluation.id}" class="report-link">
                            Rapport ${type}
                        </a>
                    `).join('')}
                </div>
            </div>
            ` : ''}
        `;
    }
    
    /**
     * Calcule la durée entre deux dates ISO
     * @param {string} startTimeIso - Date de début au format ISO
     * @param {string} endTimeIso - Date de fin au format ISO
     * @returns {string} Durée formatée
     */
    function calculateDuration(startTimeIso, endTimeIso) {
        const start = new Date(startTimeIso);
        const end = new Date(endTimeIso);
        
        const durationMs = end - start;
        const seconds = Math.floor(durationMs / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }
    
    /**
     * Gère les notifications WebSocket pour les QCM
     * @param {Object} data - Données de la notification
     */
    function handleQcmUpdates(data) {
        if (data.type !== 'qcm_generated' || !data.qcm) return;
        
        // Vérifier si c'est l'évaluation courante
        if (data.evaluation_id !== currentEvaluationId) return;
        
        // Masquer le message vide
        qcmEmptyEl.style.display = 'none';
        
        // Créer l'élément QCM
        const qcmEl = createQcmElement(data.qcm);
        
        // Ajouter au début de la liste
        qcmListEl.insertBefore(qcmEl, qcmListEl.firstChild);
        
        // Mettre en évidence le nouveau QCM
        qcmEl.classList.add('highlight');
        setTimeout(() => {
            qcmEl.classList.remove('highlight');
        }, 3000);
    }
    
    /**
     * Gère les notifications WebSocket pour le statut des évaluations
     * @param {Object} data - Données de la notification
     */
    function handleEvaluationStatus(data) {
        if (data.type !== 'evaluation_status' || !data.evaluation_id) return;
        
        // Vérifier si c'est l'évaluation courante
        if (data.evaluation_id !== currentEvaluationId) return;
        
        // Mettre à jour l'affichage
        updateEvaluationStatus({
            id: data.evaluation_id,
            status: data.status,
            progress: data.progress,
            total_qcm: data.total_qcm,
            completed_qcm: data.completed_qcm
        });
        
        // Si l'évaluation est terminée, rafraîchir la liste
        if (data.status === 'completed' || data.status === 'failed') {
            setTimeout(loadEvaluations, 1000);
        }
    }
    
    /**
     * Met à jour l'affichage du statut de l'évaluation
     * @param {Object} evaluation - Données de l'évaluation
     */
    function updateEvaluationStatus(evaluation) {
        evalStatusEl.textContent = evaluation.status;
        
        // Définir la classe de statut
        evalStatusEl.className = `status-${evaluation.status}`;
        
        // Texte détaillé
        if (evaluation.status === 'running') {
            evalDetailsEl.textContent = 'Évaluation en cours...';
        } else if (evaluation.status === 'pending') {
            evalDetailsEl.textContent = 'En attente de démarrage...';
        } else if (evaluation.status === 'completed') {
            evalDetailsEl.textContent = `Terminée le ${Utils.formatDate(evaluation.end_time, true)}`;
        } else if (evaluation.status === 'failed') {
            evalDetailsEl.textContent = `Échec: ${evaluation.error || 'Erreur inconnue'}`;
        }
        
        // Mettre à jour la barre de progression
        const progress = evaluation.progress || 0;
        evalProgressEl.style.width = `${progress}%`;
        evalProgressTextEl.textContent = `${Math.round(progress)}%`;
        
        // Mettre à jour le compteur de QCM
        const totalQcm = evaluation.total_qcm || 0;
        const completedQcm = evaluation.completed_qcm || 0;
        evalQcmCountEl.textContent = `${completedQcm}/${totalQcm} QCM`;
    }
});