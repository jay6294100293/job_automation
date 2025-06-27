// Dashboard JavaScript functionality

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    loadRealtimeUpdates();
    setupEventListeners();

    // Update profile completion
    if (document.getElementById('profileCompletionBar')) {
        updateProfileCompletion();

        // Refresh every 5 minutes (if user keeps the dashboard open)
        setInterval(updateProfileCompletion, 300000);
    }

    // Update current time
    function updateTime() {
        const now = new Date();
        const timeString = now.toLocaleString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = timeString;
        }
    }

    updateTime();
    setInterval(updateTime, 60000);

    // Animate metrics on load
    const metricValues = document.querySelectorAll('.metric-value');
    metricValues.forEach((metric, index) => {
        const finalValue = parseInt(metric.dataset.value) || 0;
        let currentValue = 0;
        const increment = finalValue / 30;

        setTimeout(() => {
            const timer = setInterval(() => {
                currentValue += increment;
                if (currentValue >= finalValue) {
                    currentValue = finalValue;
                    clearInterval(timer);
                }

                if (metric.textContent.includes('%')) {
                    metric.textContent = Math.round(currentValue) + '%';
                } else {
                    metric.textContent = Math.round(currentValue);
                }
            }, 50);
        }, index * 200);
    });

    // Animate progress bars
    setTimeout(() => {
        const progressBars = document.querySelectorAll('.progress-fill');
        progressBars.forEach((bar, index) => {
            const width = bar.dataset.width + '%';
            setTimeout(() => {
                bar.style.width = width;
            }, index * 100);
        });
    }, 500);
});

function initializeDashboard() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize progress bars with animation
    animateProgressBars();

    // Initialize counter animations
    animateCounters();

    // Setup auto-refresh for dashboard data
    setInterval(refreshDashboardData, 30000); // Refresh every 30 seconds
}

function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-bar');
    progressBars.forEach(bar => {
        const width = bar.style.width || bar.getAttribute('data-width');
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width;
        }, 100);
    });
}

function animateCounters() {
    const counters = document.querySelectorAll('[data-counter]');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-counter'));
        const duration = 2000; // 2 seconds
        const increment = target / (duration / 16); // 60fps
        let current = 0;

        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            counter.textContent = Math.floor(current);
        }, 16);
    });
}

function loadRealtimeUpdates() {
    // Check for new notifications
    fetch('/api/notifications/')
        .then(response => response.json())
        .then(data => {
            updateNotificationBadge(data.count);
            if (data.new_notifications) {
                showNotifications(data.new_notifications);
            }
        })
        .catch(error => console.error('Error loading notifications:', error));
}

function refreshDashboardData() {
    fetch('/api/dashboard/stats/')
        .then(response => response.json())
        .then(data => {
            updateDashboardStats(data);
        })
        .catch(error => console.error('Error refreshing dashboard:', error));
}

function updateDashboardStats(data) {
    // Update statistics cards
    const stats = {
        'total-applications': data.total_applications,
        'response-rate': data.response_rate + '%',
        'interviews-scheduled': data.interviews_scheduled,
        'due-followups': data.due_followups
    };

    Object.entries(stats).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });

    // Update pipeline data
    updatePipelineData(data.pipeline_data);
}

function updatePipelineData(pipelineData) {
    Object.entries(pipelineData).forEach(([status, count]) => {
        const element = document.querySelector(`[data-pipeline="${status}"] .badge`);
        if (element) {
            element.textContent = count;
        }
    });
}

function setupEventListeners() {
    // Quick action buttons
    const quickSearchBtn = document.getElementById('quick-search-btn');
    if (quickSearchBtn) {
        quickSearchBtn.addEventListener('click', handleQuickSearch);
    }

    const bulkFollowupBtn = document.getElementById('bulk-followup-btn');
    if (bulkFollowupBtn) {
        bulkFollowupBtn.addEventListener('click', handleBulkFollowup);
    }

    // Pipeline drag and drop
    setupPipelineDragDrop();

    // Search functionality
    const searchInput = document.getElementById('dashboard-search');
    if (searchInput) {
        searchInput.addEventListener('input', handleDashboardSearch);
    }
}

function handleQuickSearch() {
    // Show search configuration modal or redirect
    if (window.searchConfigs && window.searchConfigs.length > 0) {
        showQuickSearchModal();
    } else {
        window.location.href = '/jobs/search-config/create/';
    }
}

function showQuickSearchModal() {
    const modal = new bootstrap.Modal(document.getElementById('quickSearchModal'));
    modal.show();
}

function handleBulkFollowup() {
    window.location.href = '/followups/dashboard/';
}

function setupPipelineDragDrop() {
    const pipelineItems = document.querySelectorAll('.pipeline-item');
    const pipelineColumns = document.querySelectorAll('.pipeline-column');

    pipelineItems.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
    });

    pipelineColumns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragenter', handleDragEnter);
        column.addEventListener('dragleave', handleDragLeave);
    });
}

function handleDragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.dataset.applicationId);
    e.target.classList.add('dragging');
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
}

function handleDragOver(e) {
    e.preventDefault();
}

function handleDragEnter(e) {
    e.target.closest('.pipeline-column').classList.add('drag-over');
}

function handleDragLeave(e) {
    if (!e.target.closest('.pipeline-column').contains(e.relatedTarget)) {
        e.target.closest('.pipeline-column').classList.remove('drag-over');
    }
}

function handleDrop(e) {
    e.preventDefault();
    const applicationId = e.dataTransfer.getData('text/plain');
    const newStatus = e.target.closest('.pipeline-column').dataset.status;
    const column = e.target.closest('.pipeline-column');

    column.classList.remove('drag-over');

    updateApplicationStatus(applicationId, newStatus);
}

function updateApplicationStatus(applicationId, newStatus) {
    fetch(`/api/applications/${applicationId}/update-status/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({
            status: newStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Status updated successfully', 'success');
            refreshDashboardData();
        } else {
            showToast('Failed to update status', 'error');
        }
    })
    .catch(error => {
        console.error('Error updating status:', error);
        showToast('Failed to update status', 'error');
    });
}

function handleDashboardSearch(e) {
    const searchTerm = e.target.value.toLowerCase();
    const searchableElements = document.querySelectorAll('[data-searchable]');

    searchableElements.forEach(element => {
        const text = element.textContent.toLowerCase();
        const isVisible = text.includes(searchTerm);
        element.style.display = isVisible ? '' : 'none';
    });
}

// Profile completion function
function updateProfileCompletion() {
    fetch('/accounts/profile-completion/')
        .then(response => response.json())
        .then(data => {
            // Update progress bar
            const progressBar = document.getElementById('profileCompletionBar');
            if (progressBar) {
                progressBar.style.width = `${data.completion_percentage}%`;
                progressBar.setAttribute('aria-valuenow', data.completion_percentage);

                // Change color based on completion
                if (data.completion_percentage < 30) {
                    progressBar.className = 'progress-bar bg-danger';
                } else if (data.completion_percentage < 70) {
                    progressBar.className = 'progress-bar bg-warning';
                } else {
                    progressBar.className = 'progress-bar bg-success';
                }
            }

            // Update missing fields
            const missingFieldsContainer = document.getElementById('missingFieldsContainer');
            if (missingFieldsContainer && data.missing_fields.length > 0) {
                const missingText = `Missing: ${data.missing_fields.join(', ')}`;
                missingFieldsContainer.textContent = data.total_missing > 3 ?
                    `${missingText} and ${data.total_missing - 3} more` : missingText;
            } else if (missingFieldsContainer) {
                missingFieldsContainer.textContent = 'Profile complete!';
            }
        })
        .catch(error => console.error('Error updating profile completion:', error));
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

function updateNotificationBadge(count) {
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

function showNotifications(notifications) {
    notifications.forEach(notification => {
        showToast(notification.message, notification.type);
    });
}

// Close notification
function closeNotification(button) {
    const notification = button.closest('.notification-banner');
    notification.style.opacity = '0';
    notification.style.transform = 'translateY(-20px)';
    setTimeout(() => {
        notification.remove();
    }, 300);
}

// Start automation
function startAutomation() {
    if (confirm('Start automated job search? This will use your active search configurations.')) {
        const btn = event.target;
        const originalHTML = btn.innerHTML;

        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting...';
        btn.disabled = true;

        // Simulate automation start
        setTimeout(() => {
            alert('Automation started! You will receive notifications as jobs are found and processed.');
            btn.innerHTML = originalHTML;
            btn.disabled = false;
        }, 2000);
    }
}

// Send bulk follow-ups
function sendBulkFollowups(event) {
    event.preventDefault();

    if (confirm('Send follow-up emails for all pending applications?')) {
        const card = event.target.closest('.quick-action-card');
        const originalContent = card.innerHTML;

        card.innerHTML = `
            <div class="quick-action-icon">
                <i class="fas fa-spinner fa-spin"></i>
            </div>
            <div class="quick-action-title">Sending...</div>
            <div class="quick-action-desc">Please wait</div>
        `;

        // Simulate API call
        setTimeout(() => {
            alert('Follow-ups sent successfully!');
            card.innerHTML = originalContent;
        }, 2000);
    }
}

// Generate all documents
function generateAllDocuments(event) {
    event.preventDefault();

    if (confirm('Generate documents for all recent applications?')) {
        const card = event.target.closest('.quick-action-card');
        const originalContent = card.innerHTML;

        card.innerHTML = `
            <div class="quick-action-icon">
                <i class="fas fa-spinner fa-spin"></i>
            </div>
            <div class="quick-action-title">Generating...</div>
            <div class="quick-action-desc">This may take a few minutes</div>
        `;

        // Simulate API call
        setTimeout(() => {
            alert('Documents generated successfully!');
            card.innerHTML = originalContent;
        }, 3000);
    }
}

// Utility function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Export functions for use in other scripts
window.dashboard = {
    refreshData: refreshDashboardData,
    showToast: showToast,
    updateApplicationStatus: updateApplicationStatus,
    updateProfileCompletion: updateProfileCompletion
};

// // Dashboard JavaScript functionality
//
// // Initialize dashboard when DOM is loaded
// document.addEventListener('DOMContentLoaded', function() {
//     initializeDashboard();
//     loadRealtimeUpdates();
//     setupEventListeners();
// });
//
// function initializeDashboard() {
//     // Initialize tooltips
//     var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
//     var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
//         return new bootstrap.Tooltip(tooltipTriggerEl);
//     });
//
//     // Initialize progress bars with animation
//     animateProgressBars();
//
//     // Initialize counter animations
//     animateCounters();
//
//     // Setup auto-refresh for dashboard data
//     setInterval(refreshDashboardData, 30000); // Refresh every 30 seconds
// }
//
// function animateProgressBars() {
//     const progressBars = document.querySelectorAll('.progress-bar');
//     progressBars.forEach(bar => {
//         const width = bar.style.width || bar.getAttribute('data-width');
//         bar.style.width = '0%';
//         setTimeout(() => {
//             bar.style.width = width;
//         }, 100);
//     });
// }
//
// function animateCounters() {
//     const counters = document.querySelectorAll('[data-counter]');
//     counters.forEach(counter => {
//         const target = parseInt(counter.getAttribute('data-counter'));
//         const duration = 2000; // 2 seconds
//         const increment = target / (duration / 16); // 60fps
//         let current = 0;
//
//         const timer = setInterval(() => {
//             current += increment;
//             if (current >= target) {
//                 current = target;
//                 clearInterval(timer);
//             }
//             counter.textContent = Math.floor(current);
//         }, 16);
//     });
// }
//
// function loadRealtimeUpdates() {
//     // Check for new notifications
//     fetch('/api/notifications/')
//         .then(response => response.json())
//         .then(data => {
//             updateNotificationBadge(data.count);
//             if (data.new_notifications) {
//                 showNotifications(data.new_notifications);
//             }
//         })
//         .catch(error => console.error('Error loading notifications:', error));
// }
//
// function refreshDashboardData() {
//     fetch('/api/dashboard/stats/')
//         .then(response => response.json())
//         .then(data => {
//             updateDashboardStats(data);
//         })
//         .catch(error => console.error('Error refreshing dashboard:', error));
// }
//
// function updateDashboardStats(data) {
//     // Update statistics cards
//     const stats = {
//         'total-applications': data.total_applications,
//         'response-rate': data.response_rate + '%',
//         'interviews-scheduled': data.interviews_scheduled,
//         'due-followups': data.due_followups
//     };
//
//     Object.entries(stats).forEach(([id, value]) => {
//         const element = document.getElementById(id);
//         if (element) {
//             element.textContent = value;
//         }
//     });
//
//     // Update pipeline data
//     updatePipelineData(data.pipeline_data);
// }
//
// function updatePipelineData(pipelineData) {
//     Object.entries(pipelineData).forEach(([status, count]) => {
//         const element = document.querySelector(`[data-pipeline="${status}"] .badge`);
//         if (element) {
//             element.textContent = count;
//         }
//     });
// }
//
// function setupEventListeners() {
//     // Quick action buttons
//     const quickSearchBtn = document.getElementById('quick-search-btn');
//     if (quickSearchBtn) {
//         quickSearchBtn.addEventListener('click', handleQuickSearch);
//     }
//
//     const bulkFollowupBtn = document.getElementById('bulk-followup-btn');
//     if (bulkFollowupBtn) {
//         bulkFollowupBtn.addEventListener('click', handleBulkFollowup);
//     }
//
//     // Pipeline drag and drop
//     setupPipelineDragDrop();
//
//     // Search functionality
//     const searchInput = document.getElementById('dashboard-search');
//     if (searchInput) {
//         searchInput.addEventListener('input', handleDashboardSearch);
//     }
// }
//
// function handleQuickSearch() {
//     // Show search configuration modal or redirect
//     if (window.searchConfigs && window.searchConfigs.length > 0) {
//         showQuickSearchModal();
//     } else {
//         window.location.href = '/jobs/search-config/create/';
//     }
// }
//
// function showQuickSearchModal() {
//     const modal = new bootstrap.Modal(document.getElementById('quickSearchModal'));
//     modal.show();
// }
//
// function handleBulkFollowup() {
//     window.location.href = '/followups/dashboard/';
// }
//
// function setupPipelineDragDrop() {
//     const pipelineItems = document.querySelectorAll('.pipeline-item');
//     const pipelineColumns = document.querySelectorAll('.pipeline-column');
//
//     pipelineItems.forEach(item => {
//         item.addEventListener('dragstart', handleDragStart);
//         item.addEventListener('dragend', handleDragEnd);
//     });
//
//     pipelineColumns.forEach(column => {
//         column.addEventListener('dragover', handleDragOver);
//         column.addEventListener('drop', handleDrop);
//         column.addEventListener('dragenter', handleDragEnter);
//         column.addEventListener('dragleave', handleDragLeave);
//     });
// }
//
// function handleDragStart(e) {
//     e.dataTransfer.setData('text/plain', e.target.dataset.applicationId);
//     e.target.classList.add('dragging');
// }
//
// function handleDragEnd(e) {
//     e.target.classList.remove('dragging');
// }
//
// function handleDragOver(e) {
//     e.preventDefault();
// }
//
// function handleDragEnter(e) {
//     e.target.closest('.pipeline-column').classList.add('drag-over');
// }
//
// function handleDragLeave(e) {
//     if (!e.target.closest('.pipeline-column').contains(e.relatedTarget)) {
//         e.target.closest('.pipeline-column').classList.remove('drag-over');
//     }
// }
//
// function handleDrop(e) {
//     e.preventDefault();
//     const applicationId = e.dataTransfer.getData('text/plain');
//     const newStatus = e.target.closest('.pipeline-column').dataset.status;
//     const column = e.target.closest('.pipeline-column');
//
//     column.classList.remove('drag-over');
//
//     updateApplicationStatus(applicationId, newStatus);
// }
//
// function updateApplicationStatus(applicationId, newStatus) {
//     fetch(`/api/applications/${applicationId}/update-status/`, {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'X-CSRFToken': getCookie('csrftoken')
//         },
//         body: JSON.stringify({
//             status: newStatus
//         })
//     })
//     .then(response => response.json())
//     .then(data => {
//         if (data.success) {
//             showToast('Status updated successfully', 'success');
//             refreshDashboardData();
//         } else {
//             showToast('Failed to update status', 'error');
//         }
//     })
//     .catch(error => {
//         console.error('Error updating status:', error);
//         showToast('Failed to update status', 'error');
//     });
// }
//
// function handleDashboardSearch(e) {
//     const searchTerm = e.target.value.toLowerCase();
//     const searchableElements = document.querySelectorAll('[data-searchable]');
//
//     searchableElements.forEach(element => {
//         const text = element.textContent.toLowerCase();
//         const isVisible = text.includes(searchTerm);
//         element.style.display = isVisible ? '' : 'none';
//     });
// }
//
// function showToast(message, type = 'info') {
//     const toastContainer = document.getElementById('toast-container') || createToastContainer();
//
//     const toast = document.createElement('div');
//     toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
//     toast.setAttribute('role', 'alert');
//
//     toast.innerHTML = `
//         <div class="d-flex">
//             <div class="toast-body">
//                 ${message}
//             </div>
//             <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
//         </div>
//     `;
//
//     toastContainer.appendChild(toast);
//
//     const bsToast = new bootstrap.Toast(toast);
//     bsToast.show();
//
//     // Remove toast element after it's hidden
//     toast.addEventListener('hidden.bs.toast', () => {
//         toast.remove();
//     });
// }
//
// function createToastContainer() {
//     const container = document.createElement('div');
//     container.id = 'toast-container';
//     container.className = 'toast-container position-fixed top-0 end-0 p-3';
//     container.style.zIndex = '1055';
//     document.body.appendChild(container);
//     return container;
// }
//
// function updateNotificationBadge(count) {
//     const badge = document.querySelector('.notification-badge');
//     if (badge) {
//         badge.textContent = count;
//         badge.style.display = count > 0 ? 'inline-block' : 'none';
//     }
// }
//
// function showNotifications(notifications) {
//     notifications.forEach(notification => {
//         showToast(notification.message, notification.type);
//     });
// }
//
// // Utility function to get CSRF token
// function getCookie(name) {
//     let cookieValue = null;
//     if (document.cookie && document.cookie !== '') {
//         const cookies = document.cookie.split(';');
//         for (let i = 0; i < cookies.length; i++) {
//             const cookie = cookies[i].trim();
//             if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                 cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                 break;
//             }
//         }
//     }
//     return cookieValue;
// }
//
// // Export functions for use in other scripts
// window.dashboard = {
//     refreshData: refreshDashboardData,
//     showToast: showToast,
//     updateApplicationStatus: updateApplicationStatus
// };