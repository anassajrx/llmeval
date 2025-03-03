/**
 * Script pour la page de gestion des documents
 */

document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const uploadZoneEl = document.getElementById('upload-zone');
    const fileInputEl = document.getElementById('file-input');
    const uploadBtnEl = document.getElementById('upload-btn');
    const documentsTableBodyEl = document.getElementById('documents-table-body');
    const searchDocsEl = document.getElementById('search-docs');
    
    // Initialiser les modals
    const documentModal = Utils.initModal('document-modal');
    
    // Charger les documents
    loadDocuments();
    
    // Écouter les événements
    uploadBtnEl.addEventListener('click', () => {
        fileInputEl.click();
    });
    
    fileInputEl.addEventListener('change', handleFileSelection);
    
    // Gestion du drag & drop
    uploadZoneEl.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZoneEl.classList.add('highlight');
    });
    
    uploadZoneEl.addEventListener('dragleave', () => {
        uploadZoneEl.classList.remove('highlight');
    });
    
    uploadZoneEl.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZoneEl.classList.remove('highlight');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });
    
    // Recherche de documents
    searchDocsEl.addEventListener('input', () => {
        const searchTerm = searchDocsEl.value.toLowerCase();
        const rows = documentsTableBodyEl.querySelectorAll('tr[data-document-id]');
        
        rows.forEach(row => {
            const documentName = row.querySelector('[data-document-name]').textContent.toLowerCase();
            if (documentName.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
    
    /**
     * Charge la liste des documents
     */
    async function loadDocuments() {
        try {
            const response = await fetch('/api/documents');
            const data = await response.json();
            
            renderDocumentsList(data.documents || []);
        } catch (error) {
            console.error('Erreur lors du chargement des documents:', error);
            Utils.showToast('Erreur lors du chargement des documents', 'error');
        }
    }
    
    /**
     * Affiche la liste des documents
     * @param {Array} documents - Liste des documents
     */
    function renderDocumentsList(documents) {
        // Vider la table
        documentsTableBodyEl.innerHTML = '';
        
        if (documents.length === 0) {
            documentsTableBodyEl.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">Aucun document disponible</td>
                </tr>
            `;
            return;
        }
        
        // Ajouter chaque document
        documents.forEach(doc => {
            const row = document.createElement('tr');
            row.setAttribute('data-document-id', doc.id);
            
            // Nom du document
            const nameCell = document.createElement('td');
            nameCell.setAttribute('data-document-name', '');
            nameCell.textContent = doc.original_name;
            row.appendChild(nameCell);
            
            // Date d'import
            const dateCell = document.createElement('td');
            dateCell.textContent = Utils.formatDate(doc.upload_date, true);
            row.appendChild(dateCell);
            
            // Taille
            const sizeCell = document.createElement('td');
            sizeCell.textContent = Utils.formatFileSize(doc.size);
            row.appendChild(sizeCell);
            
            // Statut
            const statusCell = document.createElement('td');
            const statusEl = document.createElement('span');
            statusEl.className = `status-${doc.status === 'available' ? 'completed' : doc.status === 'missing' ? 'failed' : 'pending'}`;
            statusEl.textContent = doc.status === 'available' ? 'Disponible' : doc.status === 'missing' ? 'Manquant' : 'En traitement';
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
            viewBtn.addEventListener('click', () => showDocumentDetails(doc.id));
            actionsCell.appendChild(viewBtn);
            
            // Bouton supprimer
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'action-btn delete-btn';
            deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
            deleteBtn.title = 'Supprimer';
            deleteBtn.addEventListener('click', () => deleteDocument(doc.id));
            actionsCell.appendChild(deleteBtn);
            
            row.appendChild(actionsCell);
            
            documentsTableBodyEl.appendChild(row);
        });
    }
    
    /**
     * Gère la sélection d'un fichier via l'input
     */
    function handleFileSelection(event) {
        const file = event.target.files[0];
        if (file) {
            handleFileUpload(file);
        }
    }
    
    /**
     * Gère le téléchargement d'un fichier
     * @param {File} file - Fichier à télécharger
     */
     // Correction dans la fonction handleFileUpload

async function handleFileUpload(file) {
    // Vérifier si c'est un PDF
    if (!file.type.includes('pdf')) {
        Utils.showToast('Seuls les fichiers PDF sont acceptés', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        // Afficher un message de chargement
        Utils.showToast('Téléchargement en cours...', 'info');
        
        const response = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            Utils.showToast(`Erreur: ${result.error}`, 'error');
            return;
        }
        
        // Mettre à jour manuellement la liste des documents sur la page
        // Au lieu d'appeler seulement loadDocuments()
        if (result.id && result.original_name && result.status === "available") {
            const doc = {
                id: result.id,
                original_name: result.original_name,
                upload_date: result.upload_date,
                size: result.size,
                status: result.status
            };
            
            // Option 1: Ajouter directement le document à la liste sans recharger
            addDocumentToList(doc);
            
            // Option 2: Ou recharger la liste complète
            await loadDocuments();
        } else {
            // Si le document n'est pas immédiatement disponible, recharger après un délai
            setTimeout(loadDocuments, 1000);
        }
        
        // Afficher un message de succès
        Utils.showToast('Document téléchargé avec succès', 'success');
        
        // Réinitialiser l'input file
        fileInputEl.value = '';
        
    } catch (error) {
        console.error('Erreur lors du téléchargement:', error);
        Utils.showToast('Erreur lors du téléchargement', 'error');
    }
}

// Nouvelle fonction pour ajouter un document à la liste
function addDocumentToList(doc) {
    // Supprimer le message "pas de documents" s'il existe
    const emptyRow = documentsTableBodyEl.querySelector('.empty-state');
    if (emptyRow) {
        emptyRow.closest('tr').remove();
    }
    
    const row = document.createElement('tr');
    row.setAttribute('data-document-id', doc.id);
    
    // Nom du document
    const nameCell = document.createElement('td');
    nameCell.setAttribute('data-document-name', '');
    nameCell.textContent = doc.original_name;
    row.appendChild(nameCell);
    
    // Date d'import
    const dateCell = document.createElement('td');
    dateCell.textContent = Utils.formatDate(doc.upload_date, true);
    row.appendChild(dateCell);
    
    // Taille
    const sizeCell = document.createElement('td');
    sizeCell.textContent = Utils.formatFileSize(doc.size);
    row.appendChild(sizeCell);
    
    // Statut
    const statusCell = document.createElement('td');
    const statusEl = document.createElement('span');
    statusEl.className = `status-${doc.status === 'available' ? 'completed' : doc.status === 'missing' ? 'failed' : 'pending'}`;
    statusEl.textContent = doc.status === 'available' ? 'Disponible' : doc.status === 'missing' ? 'Manquant' : 'En traitement';
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
    viewBtn.addEventListener('click', () => showDocumentDetails(doc.id));
    actionsCell.appendChild(viewBtn);
    
    // Bouton supprimer
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'action-btn delete-btn';
    deleteBtn.innerHTML = '<i class="fas fa-trash"></i>';
    deleteBtn.title = 'Supprimer';
    deleteBtn.addEventListener('click', () => deleteDocument(doc.id));
    actionsCell.appendChild(deleteBtn);
    
    row.appendChild(actionsCell);
    
    // Ajouter au début de la table
    documentsTableBodyEl.insertBefore(row, documentsTableBodyEl.firstChild);
}
    
    /**
     * Affiche les détails d'un document
     * @param {string} documentId - ID du document
     */
    async function showDocumentDetails(documentId) {
        try {
            // Afficher le modal avec un message de chargement
            documentModal.setContent('<div class="loading">Chargement des détails...</div>');
            documentModal.open();
            
            // Charger les détails du document
            const response = await fetch(`/api/documents/${documentId}`);
            const document = await response.json();
            
            // Créer le contenu du modal
            const content = document ? createDocumentDetailsContent(document) : '<div class="error">Document non trouvé</div>';
            
            // Mettre à jour le contenu du modal
            documentModal.setContent(content);
            
        } catch (error) {
            console.error('Erreur lors du chargement des détails du document:', error);
            documentModal.setContent('<div class="error">Erreur lors du chargement des détails</div>');
        }
    }
    
    /**
     * Crée le contenu HTML pour les détails d'un document
     * @param {Object} document - Données du document
     * @returns {string} Contenu HTML
     */
    function createDocumentDetailsContent(document) {
        return `
            <div class="document-details">
                <div class="detail-item">
                    <div class="detail-label">Nom:</div>
                    <div class="detail-value">${document.original_name}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">ID:</div>
                    <div class="detail-value">${document.id}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Date d'import:</div>
                    <div class="detail-value">${Utils.formatDate(document.upload_date, true)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Taille:</div>
                    <div class="detail-value">${Utils.formatFileSize(document.size)}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">Statut:</div>
                    <div class="detail-value">
                        <span class="status-${document.status === 'available' ? 'completed' : document.status === 'missing' ? 'failed' : 'pending'}">
                            ${document.status === 'available' ? 'Disponible' : document.status === 'missing' ? 'Manquant' : 'En traitement'}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Supprime un document
     * @param {string} documentId - ID du document
     */
    async function deleteDocument(documentId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer ce document ?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/documents/${documentId}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Supprimer la ligne du tableau
                const row = documentsTableBodyEl.querySelector(`tr[data-document-id="${documentId}"]`);
                if (row) {
                    row.remove();
                }
                
                // Si plus aucun document, afficher le message vide
                if (documentsTableBodyEl.querySelectorAll('tr[data-document-id]').length === 0) {
                    documentsTableBodyEl.innerHTML = `
                        <tr>
                            <td colspan="5" class="empty-state">Aucun document disponible</td>
                        </tr>
                    `;
                }
                
                Utils.showToast('Document supprimé avec succès', 'success');
            } else {
                Utils.showToast(`Erreur: ${result.error || 'Échec de la suppression'}`, 'error');
            }
            
        } catch (error) {
            console.error('Erreur lors de la suppression du document:', error);
            Utils.showToast('Erreur lors de la suppression du document', 'error');
        }
    }
});