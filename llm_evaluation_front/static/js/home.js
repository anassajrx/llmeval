/**
 * Script pour la page d'accueil (tableau de bord)
 */

document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const documentsCountEl = document.getElementById('documents-count');
    const evaluationsCountEl = document.getElementById('evaluations-count');
    const qcmCountEl = document.getElementById('qcm-count');
    const successRateEl = document.getElementById('success-rate');
    const criteriaChartEl = document.getElementById('criteria-chart');
    const activityLogEl = document.getElementById('activity-log');
    const recentEvaluationsBodyEl = document.getElementById('recent-evaluations-body');
    
    // Variables
    let criteriaChart = null;
    
    // Charger les données initiales
    loadDashboardData();
    
    // Connexion aux WebSockets pour les mises à jour en temps réel
    WebSocketManager.connect('notifications', handleNotifications);
    
    /**
     * Charge les données du tableau de bord
     */
    async function loadDashboardData() {
        try {
            // Charger les documents
            const documentsResponse = await fetch('/api/documents');
            const documentsData = await documentsResponse.json();
            const documents = documentsData.documents || [];
            
            // Charger les évaluations
            const evaluationsResponse = await fetch('/api/evaluations');
            const evaluationsData = await evaluationsResponse.json();
            const evaluations = evaluationsData.evaluations || [];
            
            // Charger les statistiques LLM
            const llmStatsResponse = await fetch('/api/llm/statistics');
            const llmStats = await llmStatsResponse.json();
            
            // Mettre à jour les compteurs
            updateCounters(documents, evaluations, llmStats);
            
            // Mettre à jour le graphique
            updateCriteriaChart(llmStats);
            
            // Mettre à jour l'historique des évaluations
            updateRecentEvaluations(evaluations);
            
        } catch (error) {
            console.error('Erreur lors du chargement des données du tableau de bord:', error);
            Utils.showToast('Erreur lors du chargement des données', 'error');
        }
    }
    
    /**
     * Met à jour les compteurs du tableau de bord
     */
    function updateCounters(documents, evaluations, llmStats) {
        documentsCountEl.textContent = documents.length;
        evaluationsCountEl.textContent = evaluations.length;
        qcmCountEl.textContent = llmStats.total_qcm || 0;
        successRateEl.textContent = ((llmStats.success_rate || 0).toFixed(1)) + '%';
    }
    
    /**
     * Met à jour le graphique des critères
     */
    function updateCriteriaChart(llmStats) {
        const criteriaScores = llmStats.criteria_scores || {};
        
        const labels = Object.keys(criteriaScores);
        const data = Object.values(criteriaScores);
        
        // Supprimer le graphique existant s'il y en a un
        if (criteriaChart) {
            criteriaChart.destroy();
        }
        
        // Créer le nouveau graphique
        criteriaChart = new Chart(criteriaChartEl, {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Score (%)',
                    data: data,
                    fill: true,
                    backgroundColor: 'rgba(134, 188, 36, 0.2)',
                    borderColor: '#86bc24',
                    pointBackgroundColor: '#86bc24',
                    pointBorderColor: '#fff',
                    pointHoverBackgroundColor: '#fff',
                    pointHoverBorderColor: '#86bc24'
                }]
            },
            options: {
                scales: {
                    r: {
                        angleLines: {
                            display: true
                        },
                        suggestedMin: 0,
                        suggestedMax: 100
                    }
                }
            }
        });
    }
    
    /**
     * Met à jour la liste des évaluations récentes
     */
    function updateRecentEvaluations(evaluations) {
        // Limiter aux 5 dernières évaluations
        const recentEvals = evaluations.slice(0, 5);
        
        if (recentEvals.length === 0) {
            recentEvaluationsBodyEl.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">Aucune évaluation récente</td>
                </tr>
            `;
            return;
        }
        
        // Vider le tableau
        recentEvaluationsBodyEl.innerHTML = '';
        
        // Ajouter les évaluations récentes
        recentEvals.forEach(evaluation => {
            const row = document.createElement('tr');
            
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
            const viewBtn = document.createElement('button');
            viewBtn.className = 'action-btn view-btn';
            viewBtn.innerHTML = '<i class="fas fa-eye"></i> Voir';
            viewBtn.addEventListener('click', () => {
                window.location.href = `/evaluations?id=${evaluation.id}`;
            });
            actionsCell.appendChild(viewBtn);
            row.appendChild(actionsCell);
            
            recentEvaluationsBodyEl.appendChild(row);
        });
    }
    
    /**
     * Gère les notifications WebSocket
     */
    function handleNotifications(data) {
        // Ajouter la notification à l'activité
        addActivityItem(data);
        
        // Rafraîchir les données si nécessaire
        if (data.type === 'evaluation_completed' || data.type === 'evaluation_error') {
            loadDashboardData();
        }
    }
    
    /**
     * Ajoute un élément à l'historique d'activité
     */
    function addActivityItem(data) {
        // Supprimer le message "Pas d'activité récente" s'il existe
        const emptyState = activityLogEl.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }
        
        // Créer l'élément d'activité
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        
        // Définir le message en fonction du type
        let message = '';
        switch (data.type) {
            case 'evaluation_started':
                message = 'Nouvelle évaluation démarrée';
                break;
            case 'evaluation_completed':
                message = 'Évaluation terminée avec succès';
                break;
            case 'evaluation_error':
                message = 'Erreur lors de l\'évaluation: ' + (data.error || 'Erreur inconnue');
                break;
            case 'qcm_generated':
                message = 'Nouveau QCM généré';
                break;
            default:
                message = data.type;
        }
        
        // Ajouter le contenu
        activityItem.innerHTML = `
            <div>${message}</div>
            <div class="activity-time">${Utils.formatDate(data.timestamp, true)}</div>
        `;
        
        // Ajouter au début de la liste
        activityLogEl.insertBefore(activityItem, activityLogEl.firstChild);
        
        // Limiter à 10 éléments
        while (activityLogEl.children.length > 10) {
            activityLogEl.removeChild(activityLogEl.lastChild);
        }
    }
});