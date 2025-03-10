/**
 * Script principal pour le système d'évaluation LLM
 * Contient des fonctions utilitaires et des gestionnaires d'événements communs
 */

// Fonctions utilitaires
const Utils = {
    /**
     * Formate une date ISO en format lisible
     * @param {string} isoDate - Date au format ISO
     * @param {boolean} includeTime - Inclure l'heure
     * @returns {string} Date formatée
     */
    formatDate: function(isoDate, includeTime = false) {
        if (!isoDate) return 'N/A';
        const date = new Date(isoDate);
        const options = { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric'
        };
        
        if (includeTime) {
            options.hour = '2-digit';
            options.minute = '2-digit';
        }
        
        return date.toLocaleDateString('fr-FR', options);
    },
    
    /**
     * Formate une taille de fichier en format lisible
     * @param {number} bytes - Taille en octets
     * @returns {string} Taille formatée
     */
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    /**
     * Tronque une chaîne si elle est trop longue
     * @param {string} str - Chaîne à tronquer
     * @param {number} maxLength - Longueur maximale
     * @returns {string} Chaîne tronquée
     */
    truncateString: function(str, maxLength = 50) {
        if (!str) return '';
        if (str.length <= maxLength) return str;
        return str.substring(0, maxLength) + '...';
    },
    
    /**
     * Crée un élément HTML avec des attributs et du contenu
     * @param {string} tag - Tag HTML
     * @param {Object} attributes - Attributs HTML
     * @param {string|HTMLElement|Array} content - Contenu
     * @returns {HTMLElement} Élément créé
     */
    createElement: function(tag, attributes = {}, content = null) {
        const element = document.createElement(tag);
        
        // Ajouter les attributs
        for (const key in attributes) {
            if (key === 'classList' && Array.isArray(attributes[key])) {
                element.classList.add(...attributes[key]);
            } else {
                element.setAttribute(key, attributes[key]);
            }
        }
        
        // Ajouter le contenu
        if (content !== null) {
            if (Array.isArray(content)) {
                content.forEach(item => {
                    if (typeof item === 'string') {
                        element.appendChild(document.createTextNode(item));
                    } else {
                        element.appendChild(item);
                    }
                });
            } else if (typeof content === 'string') {
                element.textContent = content;
            } else {
                element.appendChild(content);
            }
        }
        
        return element;
    },
    
    /**
     * Affiche un message temporaire
     * @param {string} message - Message à afficher
     * @param {string} type - Type de message (success, error, info)
     * @param {number} duration - Durée d'affichage en ms
     */
    showToast: function(message, type = 'info', duration = 3000) {
        // Créer l'élément toast s'il n'existe pas
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.position = 'fixed';
            toastContainer.style.bottom = '20px';
            toastContainer.style.right = '20px';
            toastContainer.style.zIndex = '1000';
            document.body.appendChild(toastContainer);
        }
        
        // Créer le toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.backgroundColor = type === 'error' ? '#dc3545' : 
                                      type === 'success' ? '#28a745' : '#17a2b8';
        toast.style.color = 'white';
        toast.style.padding = '10px 20px';
        toast.style.borderRadius = '4px';
        toast.style.marginTop = '10px';
        toast.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
        toast.style.minWidth = '200px';
        
        // Ajouter le toast au conteneur
        toastContainer.appendChild(toast);
        
        // Animer l'entrée
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        toast.style.transition = 'all 0.3s ease';
        
        // Forcer le reflow
        toast.offsetHeight;
        
        // Animer
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
        
        // Supprimer après un délai
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, duration);
    },
    
    /**
     * Initialise un modal
     * @param {string} modalId - ID du modal
     * @returns {Object} Fonctions pour contrôler le modal
     */
    initModal: function(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return null;
        
        const closeBtn = modal.querySelector('.close-btn');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.remove('active');
            });
        }
        
        // Fermer en cliquant à l'extérieur
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
        
        return {
            open: () => modal.classList.add('active'),
            close: () => modal.classList.remove('active'),
            setContent: (content) => {
                const contentEl = modal.querySelector('.modal-content > div:not(.close-btn)');
                if (contentEl) {
                    if (typeof content === 'string') {
                        contentEl.innerHTML = content;
                    } else {
                        contentEl.innerHTML = '';
                        contentEl.appendChild(content);
                    }
                }
            }
        };
    }
};

// Gestionnaire WebSocket
const WebSocketManager = {
    connections: {},
    
    /**
     * Initialise une connexion WebSocket
     * @param {string} channel - Nom du canal
     * @param {function} onMessageCallback - Callback pour les messages
     */
    connect: function(channel, onMessageCallback) {
        if (this.connections[channel]) {
            // Ne pas fermer la connexion si elle existe déjà - simplement réutiliser
            if (this.connections[channel].readyState === WebSocket.OPEN) {
                console.log(`WebSocket already connected: ${channel}`);
                return;
            }
            this.connections[channel].close();
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${channel}`;
        
        const socket = new WebSocket(wsUrl);
        
        socket.onopen = () => {
            console.log(`WebSocket connected: ${channel}`);
        };
        
        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            onMessageCallback(data);
        };
        
        socket.onerror = (error) => {
            console.error(`WebSocket error: ${channel}`, error);
        };
        
        socket.onclose = () => {
            console.log(`WebSocket closed: ${channel}`);
            // Tenter de se reconnecter après un délai
            setTimeout(() => {
                if (this.connections[channel] === socket) {
                    this.connect(channel, onMessageCallback);
                }
            }, 3000);
        };
        
        this.connections[channel] = socket;
    },
    
    /**
     * Ferme une connexion WebSocket
     * @param {string} channel - Nom du canal
     */
    disconnect: function(channel) {
        if (this.connections[channel]) {
            this.connections[channel].close();
            delete this.connections[channel];
        }
    }
};

// Initialisation globale
document.addEventListener('DOMContentLoaded', function() {
    // Initialiser les éléments communs ici
    console.log('Application initialisée');
});