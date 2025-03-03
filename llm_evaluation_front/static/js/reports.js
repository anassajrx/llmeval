/**
 * Script pour la page des rapports
 */

document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const reportFilterEl = document.getElementById('report-filter');
    const documentFilterContainerEl = document.getElementById('document-filter-container');
    const documentFilterEl = document.getElementById('document-filter');
    const reportsTableBodyEl = document.getElementById('reports-table-body');
    const reportContentEl = document.getElementById('report-content');
    const exportReportBtnEl = document.getElementById('export-report-btn');
    
    // Initialiser les modals
    const reportExportModal = Utils.initModal('report-export-modal');
    
    // Variables
    let currentReportId = null;
    let reports = [];
    let documents = [];
    
    // Charger les données initiales
    loadInitialData();
    
    // Écouter les événements
    reportFilterEl.addEventListener('change', filterReports);
    documentFilterEl.addEventListener('change', filterReports);
    
    exportReportBtnEl.addEventListener('click', () => {
        if (currentReportId) {
            reportExportModal.open();
        }
    });
    
    // Ajouter des gestionnaires d'événements pour les boutons d'export
    document.querySelectorAll('.export-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const format = btn.getAttribute('data-format');
            if (currentReportId && format) {
                downloadReport(currentReportId, format);
                reportExportModal.close();
            }
        });
    });
    
    // Vérifier s'il y a un ID de rapport dans l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const reportIdParam = urlParams.get('id');
    const reportTypeParam = urlParams.get('report');
    
    if (reportIdParam && reportTypeParam) {
        setTimeout(() => {
            const reportId = findReportByEvaluationAndType(reportIdParam, reportTypeParam);
            if (reportId) {
                loadReport(reportId);
            }
        }, 500);
    }
    
    /**
     * Charge les données initiales (rapports et documents)
     */
    async function loadInitialData() {
        try {
            // Charger les rapports
            const reportsResponse = await fetch('/api/reports');
            const reportsData = await reportsResponse.json();
            reports = reportsData.reports || [];
            
            renderReportsList(reports);
            
            // Charger les documents
            const documentsResponse = await fetch('/api/documents');
            const documentsData = await documentsResponse.json();
            documents = documentsData.documents || [];
            
            populateDocumentFilter(documents);
            
        } catch (error) {
            console.error('Erreur lors du chargement des données:', error);
            Utils.showToast('Erreur lors du chargement des données', 'error');
        }
    }
    
    /**
     * Remplit le filtre de documents
     * @param {Array} documents - Liste des documents
     */
    function populateDocumentFilter(documents) {
        documentFilterEl.innerHTML = '<option value="">Tous les documents</option>';
        
        const availableDocs = documents.filter(doc => doc.status === 'available');
        
        availableDocs.forEach(doc => {
            const option = document.createElement('option');
            option.value = doc.id;
            option.textContent = doc.original_name;
            documentFilterEl.appendChild(option);
        });
    }
    
    /**
     * Affiche la liste des rapports
     * @param {Array} reportsList - Liste des rapports à afficher
     */
    function renderReportsList(reportsList) {
        // Vider la table
        reportsTableBodyEl.innerHTML = '';
        
        if (reportsList.length === 0) {
            reportsTableBodyEl.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">Aucun rapport disponible</td>
                </tr>
            `;
            return;
        }
        
        // Ajouter chaque rapport
        reportsList.forEach(report => {
            const row = document.createElement('tr');
            row.setAttribute('data-report-id', report.id);
            
            // ID court
            const idCell = document.createElement('td');
            idCell.textContent = report.id.substring(0, 8) + '...';
            row.appendChild(idCell);
            
            // Date
            const dateCell = document.createElement('td');
            dateCell.textContent = Utils.formatDate(report.creation_date, true);
            row.appendChild(dateCell);
            
            // Évaluation
            const evalCell = document.createElement('td');
            evalCell.textContent = report.evaluation_id.substring(0, 8) + '...';
            row.appendChild(evalCell);
            
            // Score
            const scoreCell = document.createElement('td');
            scoreCell.textContent = report.score ? `${report.score.toFixed(1)}%` : 'N/A';
            row.appendChild(scoreCell);
            
            // Actions
            const actionsCell = document.createElement('td');
            actionsCell.className = 'table-actions';
            
            // Bouton visualiser
            const viewBtn = document.createElement('button');
            viewBtn.className = 'action-btn view-btn';
            viewBtn.innerHTML = '<i class="fas fa-eye"></i>';
            viewBtn.title = 'Visualiser';
            viewBtn.addEventListener('click', () => loadReport(report.id));
            actionsCell.appendChild(viewBtn);
            
            // Bouton exporter
            const exportBtn = document.createElement('button');
            exportBtn.className = 'action-btn';
            exportBtn.innerHTML = '<i class="fas fa-download"></i>';
            exportBtn.title = 'Exporter';
            exportBtn.addEventListener('click', () => {
                currentReportId = report.id;
                reportExportModal.open();
            });
            actionsCell.appendChild(exportBtn);
            
            row.appendChild(actionsCell);
            
            reportsTableBodyEl.appendChild(row);
        });
    }
    
    /**
     * Filtre les rapports selon les critères sélectionnés
     */
    function filterReports() {
        const filterType = reportFilterEl.value;
        const documentId = documentFilterEl.value;
        
        // Afficher/masquer le filtre de document
        documentFilterContainerEl.style.display = filterType === 'document' ? 'block' : 'none';
        
        let filteredReports = [...reports];
        
        // Appliquer le filtre
        if (filterType === 'recent') {
            // Rapports des 7 derniers jours
            const sevenDaysAgo = new Date();
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
            
            filteredReports = filteredReports.filter(report => {
                const reportDate = new Date(report.creation_date);
                return reportDate >= sevenDaysAgo;
            });
        } else if (filterType === 'document' && documentId) {
            // Rapports pour un document spécifique
            filteredReports = filteredReports.filter(report => {
                // Vérifier dans les métadonnées de l'évaluation
                // Note: Ceci est une approximation car nous n'avons pas directement l'information
                // Une meilleure implémentation nécessiterait de stocker cette relation
                return report.document_id === documentId;
            });
        }
        
        // Afficher les rapports filtrés
        renderReportsList(filteredReports);
    }
    
    /**
     * Charge et affiche un rapport
     * @param {string} reportId - ID du rapport
     */
    async function loadReport(reportId) {
        try {
            // Afficher un message de chargement
            reportContentEl.innerHTML = '<div class="loading">Chargement du rapport...</div>';
            
            // Activer le bouton d'export
            exportReportBtnEl.disabled = false;
            
            // Mémoriser l'ID du rapport courant
            currentReportId = reportId;
            
            // Mettre en évidence la ligne sélectionnée
            const rows = reportsTableBodyEl.querySelectorAll('tr');
            rows.forEach(row => {
                row.classList.remove('selected');
                if (row.getAttribute('data-report-id') === reportId) {
                    row.classList.add('selected');
                }
            });
            
            // Charger le rapport
            const response = await fetch(`/api/reports/${reportId}`);
            const report = await response.json();
            
            if (report && report.content) {
                // Afficher le contenu du rapport
                reportContentEl.innerHTML = report.content;
            } else {
                reportContentEl.innerHTML = '<div class="error">Impossible de charger le contenu du rapport</div>';
            }
            
        } catch (error) {
            console.error('Erreur lors du chargement du rapport:', error);
            reportContentEl.innerHTML = '<div class="error">Erreur lors du chargement du rapport</div>';
        }
    }
    
    /**
     * Télécharge un rapport dans un format spécifique
     * @param {string} reportId - ID du rapport
     * @param {string} format - Format de téléchargement (html, pdf, csv, json)
     */
    async function downloadReport(reportId, format) {
        try {
            // Afficher un message de chargement
            Utils.showToast(`Préparation du téléchargement en format ${format.toUpperCase()}...`, 'info');
            
            // Demander le téléchargement
            const response = await fetch(`/api/reports/download/${reportId}?format=${format}`);
            
            if (!response.ok) {
                throw new Error(`Erreur HTTP: ${response.status}`);
            }
            
            // S'il s'agit d'un JSON avec une URL de téléchargement
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();
                if (data.download_url) {
                    // Créer un lien et déclencher le téléchargement
                    const a = document.createElement('a');
                    a.href = data.download_url;
                    a.download = `report_${reportId}.${format}`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    Utils.showToast('Téléchargement démarré', 'success');
                } else {
                    throw new Error('URL de téléchargement non disponible');
                }
            } else {
                // Téléchargement direct du blob
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `report_${reportId}.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                Utils.showToast('Téléchargement démarré', 'success');
            }
            
        } catch (error) {
            console.error('Erreur lors du téléchargement du rapport:', error);
            Utils.showToast('Erreur lors du téléchargement du rapport', 'error');
        }
    }
    
    /**
     * Trouve un ID de rapport à partir de l'ID d'évaluation et du type de rapport
     * @param {string} evaluationId - ID de l'évaluation
     * @param {string} reportType - Type de rapport
     * @returns {string|null} ID du rapport ou null si non trouvé
     */
    function findReportByEvaluationAndType(evaluationId, reportType) {
        for (const report of reports) {
            if (report.evaluation_id === evaluationId) {
                return report.id;
            }
        }
        return null;
    }
});