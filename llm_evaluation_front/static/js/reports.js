/**
 * Script pour la page des rapports
 */

document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const dateFromEl = document.getElementById('date-from');
    const dateToEl = document.getElementById('date-to');
    const evaluationFilterEl = document.getElementById('evaluation-filter');
    const documentFilterEl = document.getElementById('document-filter');
    const applyFiltersBtn = document.getElementById('apply-filters-btn');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');
    const reportsTableBodyEl = document.getElementById('reports-table-body');
    const reportContentEl = document.getElementById('report-content');
    const downloadHtmlBtn = document.getElementById('download-html-btn');
    const downloadJsonBtn = document.getElementById('download-json-btn');
    const downloadCsvBtn = document.getElementById('download-csv-btn');
    
    // Variables
    let currentReportId = null;
    let reports = [];
    let evaluations = [];
    let documents = [];
    
    // Charger les données initiales
    loadInitialData();
    
    // Écouter les événements
    applyFiltersBtn.addEventListener('click', applyFilters);
    resetFiltersBtn.addEventListener('click', resetFilters);
    
    downloadHtmlBtn.addEventListener('click', () => downloadReport('html'));
    downloadJsonBtn.addEventListener('click', () => downloadReport('json'));
    downloadCsvBtn.addEventListener('click', () => downloadReport('csv'));
    
        /**
     * Charge les données initiales (rapports, évaluations, documents)
     */
    async function loadInitialData() {
        try {
            // D'abord lancer un scan des rapports pour s'assurer que tous sont indexés
            await fetch('/api/reports/scan');
            
            // Charger les rapports
            const reportsResponse = await fetch('/api/reports');
            const reportsData = await reportsResponse.json();
            reports = reportsData.reports || [];
            
            console.log("Reports loaded:", reports.length, reports);  // Log pour débogage
            
            renderReportsList(reports);
            
            // Charger les évaluations
            const evaluationsResponse = await fetch('/api/evaluations');
            const evaluationsData = await evaluationsResponse.json();
            evaluations = evaluationsData.evaluations || [];
            
            populateEvaluationFilter(evaluations);
            
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
     * Remplit le filtre d'évaluations
     * @param {Array} evaluations - Liste des évaluations
     */
    function populateEvaluationFilter(evaluations) {
        evaluationFilterEl.innerHTML = '<option value="">Toutes les évaluations</option>';
        
        const completedEvals = evaluations.filter(eval => eval.status === 'completed');
        
        completedEvals.forEach(eval => {
            const option = document.createElement('option');
            option.value = eval.id;
            option.textContent = `Éval ${eval.id.substring(0, 8)}... (${Utils.formatDate(eval.start_time)})`;
            evaluationFilterEl.appendChild(option);
        });
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
     * Applique les filtres sélectionnés
     */
    async function applyFilters() {
        try {
            const dateFrom = dateFromEl.value ? new Date(dateFromEl.value).toISOString() : null;
            const dateTo = dateToEl.value ? new Date(dateToEl.value).toISOString() : null;
            const evaluationId = evaluationFilterEl.value || null;
            const documentId = documentFilterEl.value || null;
            
            // Construire l'URL avec les paramètres de filtre
            let url = '/api/reports/filter?';
            if (dateFrom) url += `date_from=${encodeURIComponent(dateFrom)}&`;
            if (dateTo) url += `date_to=${encodeURIComponent(dateTo)}&`;
            if (evaluationId) url += `evaluation_id=${encodeURIComponent(evaluationId)}&`;
            if (documentId) url += `document_id=${encodeURIComponent(documentId)}&`;
            
            // Supprimer le dernier '&' si présent
            url = url.endsWith('&') ? url.slice(0, -1) : url;
            
            // Effectuer la requête
            const response = await fetch(url);
            const data = await response.json();
            
            // Mettre à jour la liste
            renderReportsList(data.reports || []);
            
        } catch (error) {
            console.error('Erreur lors de l\'application des filtres:', error);
            Utils.showToast('Erreur lors de l\'application des filtres', 'error');
        }
    }
    
    /**
     * Réinitialise les filtres
     */
    function resetFilters() {
        dateFromEl.value = '';
        dateToEl.value = '';
        evaluationFilterEl.value = '';
        documentFilterEl.value = '';
        
        // Recharger tous les rapports
        loadInitialData();
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
                    <td colspan="8" class="empty-state">Aucun rapport disponible</td>
                </tr>
            `;
            return;
        }
        
        // Ajouter chaque rapport
        reportsList.forEach(report => {
            // Pour chaque rapport, créer trois lignes (HTML, JSON, CSV)
            const formats = ['html', 'json', 'csv'];
            
            formats.forEach(format => {
                if (!report.report_files || !report.report_files[format]) {
                    return; // Ignorer les formats non disponibles
                }
                
                const row = document.createElement('tr');
                row.setAttribute('data-report-id', report.id);
                row.setAttribute('data-format', format);
                
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
                
                // Documents
                const docsCell = document.createElement('td');
                const docNames = report.documents ? report.documents.map(d => d.name).join(', ') : 'N/A';
                docsCell.textContent = Utils.truncateString(docNames, 30);
                docsCell.title = docNames; // Afficher le nom complet au survol
                row.appendChild(docsCell);
                
                // QCM
                const qcmCell = document.createElement('td');
                qcmCell.textContent = report.total_qcm || 'N/A';
                row.appendChild(qcmCell);
                
                // Score
                const scoreCell = document.createElement('td');
                scoreCell.textContent = report.score ? `${report.score.toFixed(1)}%` : 'N/A';
                row.appendChild(scoreCell);
                
                // Format
                const formatCell = document.createElement('td');
                formatCell.innerHTML = `<span class="format-badge format-${format}">${format.toUpperCase()}</span>`;
                row.appendChild(formatCell);
                
                // Actions
                const actionsCell = document.createElement('td');
                actionsCell.className = 'table-actions';

                // Bouton visualiser
                const viewBtn = document.createElement('button');
                viewBtn.className = 'action-btn view-btn';
                viewBtn.innerHTML = '<i class="fas fa-eye"></i>';  // Icône uniquement
                viewBtn.title = `Visualiser (${format.toUpperCase()})`;
                viewBtn.addEventListener('click', () => loadReport(report.id, format));
                actionsCell.appendChild(viewBtn);

                // Bouton télécharger
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'action-btn download-btn';
                downloadBtn.innerHTML = '<i class="fas fa-download"></i>';  // Icône uniquement
                downloadBtn.title = `Télécharger (${format.toUpperCase()})`;
                downloadBtn.addEventListener('click', () => downloadReport(format, report.id));
                actionsCell.appendChild(downloadBtn);

                row.appendChild(actionsCell);
                
                reportsTableBodyEl.appendChild(row);
            });
        });
    }
    
    /**
 * Charge et affiche un rapport
 * @param {string} reportId - ID du rapport
 * @param {string} format - Format du rapport à afficher (html, json, csv)
 */
async function loadReport(reportId, format = 'html') {
    try {
        // Afficher un message de chargement
        reportContentEl.innerHTML = '<div class="loading">Chargement du rapport...</div>';
        
        // Activer les boutons de téléchargement
        downloadHtmlBtn.disabled = false;
        downloadJsonBtn.disabled = false;
        downloadCsvBtn.disabled = false;
        
        // Mémoriser l'ID du rapport courant
        currentReportId = reportId;
        
        // Mettre en évidence la ligne sélectionnée
        const rows = reportsTableBodyEl.querySelectorAll('tr');
        rows.forEach(row => {
            row.classList.remove('selected');
            if (row.getAttribute('data-report-id') === reportId && 
                row.getAttribute('data-format') === format) {
                row.classList.add('selected');
            }
        });
        
        // Charger le rapport
        const response = await fetch(`/api/reports/${reportId}`);
        const report = await response.json();
        
        // Récupérer le chemin du fichier pour le format demandé
        const filePath = report.report_files?.[format];
        
        if (!filePath) {
            reportContentEl.innerHTML = '<div class="error">Format de rapport non disponible</div>';
            return;
        }
        
        // Charger le contenu du fichier selon le format
        const fileResponse = await fetch(`/api/reports/download/${reportId}?format=${format}`);
        
        if (!fileResponse.ok) {
            reportContentEl.innerHTML = '<div class="error">Erreur lors du chargement du fichier</div>';
            return;
        }
        
        // Traiter selon le format
        if (format === 'html') {
            // Pour HTML, utiliser un iframe
            const htmlContent = await fileResponse.text();
            
            // Créer un iframe pour isoler les styles
            const iframe = document.createElement('iframe');
            iframe.style.width = '100%';
            iframe.style.height = '600px';
            iframe.style.border = 'none';
            
            reportContentEl.innerHTML = '';
            reportContentEl.appendChild(iframe);
            
            // Écrire le contenu HTML dans l'iframe
            const doc = iframe.contentDocument || iframe.contentWindow.document;
            doc.open();
            doc.write(htmlContent);
            doc.close();
            
            // Ajuster la hauteur de l'iframe
            iframe.style.height = `${doc.body.scrollHeight + 30}px`;
            
        } else if (format === 'json') {
            // Pour JSON, afficher avec mise en forme et coloration syntaxique
            const jsonContent = await fileResponse.json();
            const pre = document.createElement('pre');
            pre.className = 'json-viewer';
            
            // Formatter le JSON avec une indentation de 2 espaces
            pre.textContent = JSON.stringify(jsonContent, null, 2);
            
            reportContentEl.innerHTML = '';
            reportContentEl.appendChild(pre);
            
            // Si disponible, on pourrait ajouter une bibliothèque de coloration syntaxique
            // comme highlight.js ici
            
        } else if (format === 'csv') {
            // Pour CSV, créer un tableau HTML
            const csvContent = await fileResponse.text();
            const table = document.createElement('table');
            table.className = 'csv-table';
            
            // Parser le CSV
            const rows = csvContent.split('\n');
            const header = rows[0].split(',');
            
            // Créer l'en-tête du tableau
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            
            header.forEach(cell => {
                const th = document.createElement('th');
                th.textContent = cell.replace(/"/g, ''); // Supprimer les guillemets
                headerRow.appendChild(th);
            });
            
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Créer le corps du tableau
            const tbody = document.createElement('tbody');
            
            // Ajouter toutes les lignes sauf l'en-tête
            for (let i = 1; i < rows.length; i++) {
                if (rows[i].trim() === '') continue; // Ignorer les lignes vides
                
                const row = document.createElement('tr');
                const cells = rows[i].split(',');
                
                cells.forEach(cell => {
                    const td = document.createElement('td');
                    td.textContent = cell.replace(/"/g, ''); // Supprimer les guillemets
                    row.appendChild(td);
                });
                
                tbody.appendChild(row);
            }
            
            table.appendChild(tbody);
            
            // Ajouter le tableau au conteneur
            reportContentEl.innerHTML = '';
            reportContentEl.appendChild(table);
        }
        
    } catch (error) {
        console.error('Erreur lors du chargement du rapport:', error);
        reportContentEl.innerHTML = '<div class="error">Erreur lors du chargement du rapport</div>';
    }
}
    
    /**
     * Télécharge un rapport dans un format spécifique
     * @param {string} format - Format de téléchargement (html, pdf, csv, json)
     * @param {string} reportId - ID du rapport (optionnel, utilise le rapport courant si non spécifié)
     */
    async function downloadReport(format, reportId = null) {
        // Utiliser le rapport courant si non spécifié
        const id = reportId || currentReportId;
        
        if (!id) {
            Utils.showToast('Aucun rapport sélectionné', 'error');
            return;
        }
        
        try {
            // Afficher un message de chargement
            Utils.showToast(`Préparation du téléchargement en format ${format.toUpperCase()}...`, 'info');
            
            // Créer l'URL de téléchargement
            const downloadUrl = `/api/reports/download/${id}?format=${format}`;
            
            // Créer un lien et déclencher le téléchargement
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `rapport_evaluation_llm_${format}.${format}`;
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            
            Utils.showToast('Téléchargement démarré', 'success');
            
        } catch (error) {
            console.error('Erreur lors du téléchargement du rapport:', error);
            Utils.showToast('Erreur lors du téléchargement du rapport', 'error');
        }
    }
});