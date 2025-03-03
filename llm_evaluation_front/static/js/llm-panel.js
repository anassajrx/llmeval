/**
 * Script pour la page LLM Panel
 */

document.addEventListener('DOMContentLoaded', function() {
    // Éléments DOM
    const llmInfoEl = document.getElementById('llm-info');
    const llmStatsEl = document.getElementById('llm-stats');
    const criteriaPerformanceChartEl = document.getElementById('criteria-performance-chart');
    const successExamplesEl = document.getElementById('success-examples');
    const failureExamplesEl = document.getElementById('failure-examples');
    
    // Variables
    let criteriaChart = null;
    
    // Charger les données
    loadLLMInfo();
    loadLLMStatistics();
    
    // Gestionnaires d'événements pour les onglets
    document.querySelectorAll('.tab-btn').forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // Activer le bouton
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            button.classList.add('active');
            
            // Afficher le contenu correspondant
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabId}-examples`).classList.add('active');
        });
    });
    
    /**
     * Charge les informations sur le LLM
     */
    async function loadLLMInfo() {
        try {
            const response = await fetch('/api/llm/info');
            const llmInfo = await response.json();
            
            renderLLMInfo(llmInfo);
        } catch (error) {
            console.error('Erreur lors du chargement des informations LLM:', error);
            llmInfoEl.innerHTML = '<div class="error">Erreur lors du chargement des informations</div>';
        }
    }
    
    /**
     * Charge les statistiques du LLM
     */
    async function loadLLMStatistics() {
        try {
            const response = await fetch('/api/llm/statistics');
            const statistics = await response.json();
            
            renderLLMStatistics(statistics);
            renderPerformanceChart(statistics);
            renderExamples(statistics);
        } catch (error) {
            console.error('Erreur lors du chargement des statistiques LLM:', error);
            llmStatsEl.innerHTML = '<div class="error">Erreur lors du chargement des statistiques</div>';
        }
    }
    
    /**
     * Affiche les informations du LLM
     * @param {Object} info - Informations sur le LLM
     */
    function renderLLMInfo(info) {
        llmInfoEl.innerHTML = '';
        
        const infoItems = [
            { label: 'Modèle', value: info.model || 'N/A' },
            { label: 'Version', value: info.version || 'N/A' },
            { label: 'Rôle', value: info.role || 'N/A' },
            { label: 'Température', value: info.temperature !== undefined ? info.temperature : 'N/A' }
        ];
        
        infoItems.forEach(item => {
            const infoItem = document.createElement('div');
            infoItem.className = 'info-item';
            
            const label = document.createElement('div');
            label.className = 'info-label';
            label.textContent = item.label;
            
            const value = document.createElement('div');
            value.className = 'info-value';
            value.textContent = item.value;
            
            infoItem.appendChild(label);
            infoItem.appendChild(value);
            llmInfoEl.appendChild(infoItem);
        });
    }
    
    /**
     * Affiche les statistiques de performance du LLM
     * @param {Object} stats - Statistiques du LLM
     */
    function renderLLMStatistics(stats) {
        llmStatsEl.innerHTML = '';
        
        // Première ligne
        const row1 = document.createElement('div');
        row1.className = 'stat-row';
        
        const overallScore = document.createElement('div');
        overallScore.className = 'stat-item';
        overallScore.innerHTML = `
            <div class="stat-label">Score Global</div>
            <div class="stat-value" id="llm-overall-score">${stats.overall_score.toFixed(1)}%</div>
        `;
        
        const successRate = document.createElement('div');
        successRate.className = 'stat-item';
        successRate.innerHTML = `
            <div class="stat-label">Taux de Succès</div>
            <div class="stat-value" id="llm-success-rate">${stats.success_rate.toFixed(1)}%</div>
        `;
        
        row1.appendChild(overallScore);
        row1.appendChild(successRate);
        llmStatsEl.appendChild(row1);
        
        // Deuxième ligne
        const row2 = document.createElement('div');
        row2.className = 'stat-row';
        
        const totalEvaluations = document.createElement('div');
        totalEvaluations.className = 'stat-item';
        totalEvaluations.innerHTML = `
            <div class="stat-label">Évaluations</div>
            <div class="stat-value">${stats.total_evaluations}</div>
        `;
        
        const totalQcm = document.createElement('div');
        totalQcm.className = 'stat-item';
        totalQcm.innerHTML = `
            <div class="stat-label">QCM Total</div>
            <div class="stat-value">${stats.total_qcm}</div>
        `;
        
        row2.appendChild(totalEvaluations);
        row2.appendChild(totalQcm);
        llmStatsEl.appendChild(row2);
    }
    
    /**
     * Affiche le graphique de performance par critère
     * @param {Object} stats - Statistiques du LLM
     */
    function renderPerformanceChart(stats) {
        const criteriaScores = stats.criteria_scores || {};
        
        const labels = Object.keys(criteriaScores);
        const data = Object.values(criteriaScores);
        
        // Supprimer le graphique existant s'il y en a un
        if (criteriaChart) {
            criteriaChart.destroy();
        }
        
        // Créer le nouveau graphique
        criteriaChart = new Chart(criteriaPerformanceChartEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Score (%)',
                    data: data,
                    backgroundColor: '#86bc24',
                    borderColor: '#6a9e0f',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Score: ${context.parsed.y.toFixed(1)}%`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Score (%)'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Affiche les exemples de réussite et d'échec
     * @param {Object} stats - Statistiques du LLM
     */
    function renderExamples(stats) {
        // Exemples de réussite
        renderExamplesList(successExamplesEl, stats.success_examples || []);
        
        // Exemples d'échec
        renderExamplesList(failureExamplesEl, stats.failure_examples || []);
    }
    
    /**
     * Affiche une liste d'exemples
     * @param {HTMLElement} container - Conteneur pour les exemples
     * @param {Array} examples - Liste des exemples
     */
    function renderExamplesList(container, examples) {
        if (examples.length === 0) {
            container.innerHTML = '<p class="empty-state">Aucun exemple disponible</p>';
            return;
        }
        
        container.innerHTML = '';
        
        examples.forEach(example => {
            const exampleEl = document.createElement('div');
            exampleEl.className = 'qcm-card';
            
            const questionEl = document.createElement('div');
            questionEl.className = 'qcm-question';
            questionEl.textContent = example.question;
            
            const metaEl = document.createElement('div');
            metaEl.className = 'qcm-meta';
            metaEl.textContent = `Critère: ${example.criterion} | Réponse du modèle: ${example.model_answer} | Réponse correcte: ${example.correct_answer}`;
            
            exampleEl.appendChild(questionEl);
            exampleEl.appendChild(metaEl);
            
            container.appendChild(exampleEl);
        });
    }
});