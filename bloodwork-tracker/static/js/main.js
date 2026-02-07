// Main JavaScript file for Blood Work Tracker

// Global configuration
const CONFIG = {
    apiUrl: '/api/v1',
    fhirApiUrl: '/fhir',
    chartColors: {
        glucose: 'rgb(75, 192, 192)',
        creatinine: 'rgb(255, 99, 132)',
        sodium: 'rgb(54, 162, 235)',
        potassium: 'rgb(255, 205, 86)',
        cholesterol: 'rgb(255, 159, 64)',
        default: 'rgb(153, 102, 255)'
    }
};

// Utility functions
const Utils = {
    formatDate: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES');
    },

    formatDateTime: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleString('es-ES');
    },

    showAlert: (message, type = 'info') => {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);

        // Auto dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alertDiv);
            bsAlert.close();
        }, 5000);
    },

    showLoading: (element) => {
        const originalHTML = element.innerHTML;
        element.innerHTML = '<span class="loading-spinner"></span> Cargando...';
        return originalHTML;
    },

    hideLoading: (element, originalHTML) => {
        element.innerHTML = originalHTML;
    },

    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// API Service
const ApiService = {
    async request(endpoint, options = {}) {
        const url = `${CONFIG.apiUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
            }
        };

        const mergedOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, mergedOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },

    async getPatients() {
        return this.request('/patients');
    },

    async getPatient(id) {
        return this.request(`/patients/${id}`);
    },

    async createPatient(data) {
        return this.request('/patients', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updatePatient(id, data) {
        return this.request(`/patients/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deletePatient(id) {
        return this.request(`/patients/${id}`, {
            method: 'DELETE'
        });
    },

    async getObservations(patientId) {
        return this.request(`/observations?patient=${patientId}`);
    },

    async getReports(patientId) {
        return this.request(`/reports?patient=${patientId}`);
    },

    async getAnalyticsTrends(patientId, biomarker, period = '6m') {
        return this.request(`/analytics/trends?patient=${patientId}&biomarker=${biomarker}&period=${period}`);
    }
};

// Chart Service
const ChartService = {
    createLineChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        const defaultOptions = {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: options.title || 'Gráfico de Tendencias'
                }
            },
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        };

        const chartOptions = { ...defaultOptions, ...options };

        return new Chart(ctx, {
            type: 'line',
            data: data,
            options: chartOptions
        });
    },

    createBarChart(canvasId, data, options = {}) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        const defaultOptions = {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: options.title || 'Gráfico de Barras'
                }
            }
        };

        const chartOptions = { ...defaultOptions, ...options };

        return new Chart(ctx, {
            type: 'bar',
            data: data,
            options: chartOptions
        });
    },

    updateChart(chart, newData) {
        chart.data = newData;
        chart.update();
    }
};

// Page-specific functionality
const Pages = {
    dashboard: {
        init: function() {
            this.loadStats();
            this.loadTrendsChart();
            this.loadRecentActivity();
        },

        loadStats: async function() {
            try {
                const [patients, reports, documents] = await Promise.all([
                    ApiService.getPatients(),
                    ApiService.getReports(),
                    // Documents would need a separate API call
                ]);

                document.getElementById('patient-count').textContent = patients.total || 0;
                document.getElementById('report-count').textContent = reports.total || 0;
                
                // Calculate alerts (abnormal values) - simplified example
                let alertCount = 0;
                for (const report of reports.reports || []) {
                    // Logic to count abnormal observations would go here
                }
                document.getElementById('alert-count').textContent = alertCount;
                
                // Document count would come from documents API
                document.getElementById('document-count').textContent = 0;
            } catch (error) {
                console.error('Error loading dashboard stats:', error);
            }
        },

        loadTrendsChart: function() {
            // Sample data - would be replaced with real API calls
            const ctx = document.getElementById('trendsChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
                    datasets: [{
                        label: 'Glucosa',
                        data: [95, 98, 102, 97, 99, 101],
                        borderColor: CONFIG.chartColors.glucose,
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }, {
                        label: 'Creatinina',
                        data: [0.9, 0.92, 0.88, 0.91, 0.93, 0.89],
                        borderColor: CONFIG.chartColors.creatinine,
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Tendencias de Biomarcadores'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    }
                }
            });
        },

        loadRecentActivity: function() {
            // Would load from API in real implementation
            console.log('Loading recent activity...');
        }
    },

    patients: {
        init: function() {
            this.bindEvents();
            this.loadPatients();
        },

        bindEvents: function() {
            const newPatientBtn = document.getElementById('new-patient-btn');
            if (newPatientBtn) {
                newPatientBtn.addEventListener('click', () => this.showCreateForm());
            }
        },

        loadPatients: async function() {
            try {
                const response = await ApiService.getPatients();
                this.renderPatients(response.patients);
            } catch (error) {
                Utils.showAlert('Error al cargar pacientes: ' + error.message, 'danger');
            }
        },

        renderPatients: function(patients) {
            const container = document.getElementById('patients-list');
            if (!container) return;

            container.innerHTML = '';

            patients.forEach(patient => {
                const patientCard = document.createElement('div');
                patientCard.className = 'col-md-6 col-lg-4 mb-4';
                patientCard.innerHTML = `
                    <div class="card patient-card h-100">
                        <div class="card-body">
                            <h5 class="card-title">${patient.name}</h5>
                            <p class="card-text">
                                <strong>ID:</strong> ${patient.id}<br>
                                <strong>Fecha Nacimiento:</strong> ${Utils.formatDate(patient.birth_date)}<br>
                                <strong>Género:</strong> ${patient.gender || 'No especificado'}
                            </p>
                            <div class="d-grid gap-2 d-md-flex justify-content-md-end">
                                <button class="btn btn-sm btn-outline-primary" onclick="Pages.patients.view(${patient.id})">
                                    Ver
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="Pages.patients.edit(${patient.id})">
                                    Editar
                                </button>
                            </div>
                        </div>
                    </div>
                `;
                container.appendChild(patientCard);
            });
        },

        showCreateForm: function() {
            // Would show modal or navigate to form in real implementation
            window.location.href = '/patients/create';
        },

        view: function(id) {
            window.location.href = `/patients/${id}`;
        },

        edit: function(id) {
            window.location.href = `/patients/${id}/edit`;
        }
    },

    observations: {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            // Bind events for observation page
            const searchInput = document.getElementById('observation-search');
            if (searchInput) {
                const debouncedSearch = Utils.debounce(this.searchObservations, 300);
                searchInput.addEventListener('input', debouncedSearch.bind(this));
            }
        },

        searchObservations: async function(event) {
            const searchTerm = event.target.value;
            // Would implement search functionality
            console.log('Searching for:', searchTerm);
        }
    },

    ai: {
        init: function() {
            this.bindEvents();
        },

        bindEvents: function() {
            const consultForm = document.getElementById('ai-consult-form');
            if (consultForm) {
                consultForm.addEventListener('submit', this.handleSubmit.bind(this));
            }
        },

        handleSubmit: async function(event) {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const question = formData.get('question');
            const provider = formData.get('provider') || 'mock';
            const patientId = formData.get('patient_id');

            if (!question.trim()) {
                Utils.showAlert('Por favor ingrese una pregunta', 'warning');
                return;
            }

            const submitBtn = event.target.querySelector('button[type="submit"]');
            const originalText = Utils.showLoading(submitBtn);

            try {
                const response = await fetch(`${CONFIG.apiUrl}/ai/consult`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
                    },
                    body: JSON.stringify({
                        question: question,
                        provider: provider,
                        context_type: 'fhir_bundle',
                        patient_id: patientId
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();

                // Display the response
                this.displayResponse(data.answer, question);

            } catch (error) {
                Utils.showAlert('Error en la consulta de IA: ' + error.message, 'danger');
            } finally {
                Utils.hideLoading(submitBtn, originalText);
            }
        },

        displayResponse: function(answer, question) {
            const responseContainer = document.getElementById('ai-response-container');
            if (!responseContainer) return;

            responseContainer.innerHTML = `
                <div class="ai-prompt">
                    <h6>Pregunta:</h6>
                    <p>${question}</p>
                </div>
                <div class="ai-response">
                    <h6>Respuesta:</h6>
                    <p>${answer}</p>
                    <small class="text-muted">Proveedor: ${localStorage.getItem('aiProvider') || 'mock'}</small>
                </div>
            `;
        }
    }
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Determine which page we're on and initialize accordingly
    const bodyClass = document.body.className;
    
    if (bodyClass.includes('dashboard-page')) {
        Pages.dashboard.init();
    } else if (bodyClass.includes('patients-page')) {
        Pages.patients.init();
    } else if (bodyClass.includes('observations-page')) {
        Pages.observations.init();
    } else if (bodyClass.includes('ai-page')) {
        Pages.ai.init();
    }

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// Export modules for testing/debugging
window.BloodWorkTracker = {
    CONFIG,
    Utils,
    ApiService,
    ChartService,
    Pages
};