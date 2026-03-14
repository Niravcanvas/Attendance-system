// static/js/ui.js - Modern UI Utilities
(function(){
    // Toast System
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    function createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'fixed top-4 right-4 z-50 space-y-3 w-80';
        document.body.appendChild(container);
        return container;
    }
    
    window.toast = function(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `px-4 py-3 rounded-lg border-l-4 transform transition-all duration-300 translate-x-full opacity-0 ${
            type === 'success' ? 'bg-success-900/30 border-success-500 text-success-300' :
            type === 'error' ? 'bg-danger-900/30 border-danger-500 text-danger-300' :
            type === 'warning' ? 'bg-warning-900/30 border-warning-500 text-warning-300' :
            'bg-primary-900/30 border-primary-500 text-primary-300'
        }`;
        
        const icon = type === 'success' ? 'fa-check-circle' :
                    type === 'error' ? 'fa-exclamation-circle' :
                    type === 'warning' ? 'fa-exclamation-triangle' :
                    'fa-info-circle';
        
        toast.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${icon} mr-3 text-lg"></i>
                <div class="flex-1 text-sm">${message}</div>
                <button class="ml-3 text-gray-300 hover:text-white transition-colors" 
                        onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-full', 'opacity-0');
            toast.classList.add('translate-x-0', 'opacity-100');
        });
        
        // Auto remove
        if (duration > 0) {
            setTimeout(() => {
                toast.classList.remove('translate-x-0', 'opacity-100');
                toast.classList.add('translate-x-full', 'opacity-0');
                setTimeout(() => toast.remove(), 300);
            }, duration);
        }
        
        return toast;
    };
    
    // Loading Overlay
    window.showLoading = function(message = 'Processing...') {
        let overlay = document.getElementById('loadingOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loadingOverlay';
            overlay.className = 'fixed inset-0 bg-black/70 z-50 hidden items-center justify-center';
            overlay.innerHTML = `
                <div class="bg-gray-800 rounded-xl p-8 shadow-2xl text-center">
                    <div class="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p class="text-white text-lg font-medium">${message}</p>
                </div>
            `;
            document.body.appendChild(overlay);
        }
        
        overlay.querySelector('p').textContent = message;
        overlay.classList.remove('hidden');
    };
    
    window.hideLoading = function() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    };
    
    // Confirm Dialog
    window.confirmAction = function(message, callback) {
        if (typeof callback !== 'function') return;
        
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md w-full">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-10 h-10 rounded-full bg-warning-900/30 flex items-center justify-center">
                        <i class="fas fa-exclamation-triangle text-warning-400"></i>
                    </div>
                    <h3 class="text-lg font-semibold text-white">Confirmation</h3>
                </div>
                <p class="text-gray-300 mb-6">${message}</p>
                <div class="flex gap-3">
                    <button class="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors" 
                            onclick="this.closest('.fixed').remove()">
                        Cancel
                    </button>
                    <button class="flex-1 px-4 py-2 bg-danger-600 hover:bg-danger-700 text-white font-medium rounded-lg transition-colors"
                            onclick="this.closest('.fixed').remove(); callback();">
                        Confirm
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on escape
        const closeOnEscape = (e) => {
            if (e.key === 'Escape') modal.remove();
        };
        document.addEventListener('keydown', closeOnEscape);
        
        // Close on background click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        // Cleanup
        modal.addEventListener('remove', () => {
            document.removeEventListener('keydown', closeOnEscape);
        });
    };
    
    // Loading state for buttons
    window.setLoading = function(element, isLoading, loadingText = 'Processing...') {
        if (isLoading) {
            element.disabled = true;
            const originalText = element.innerHTML;
            element.setAttribute('data-original-text', originalText);
            element.innerHTML = `<i class="fas fa-spinner fa-spin mr-2"></i>${loadingText}`;
        } else {
            element.disabled = false;
            const originalText = element.getAttribute('data-original-text');
            if (originalText) {
                element.innerHTML = originalText;
            }
        }
    };
    
    // Copy to clipboard
    window.copyToClipboard = function(text, successMessage = 'Copied to clipboard!') {
        navigator.clipboard.writeText(text)
            .then(() => toast(successMessage, 'success'))
            .catch(err => {
                console.error('Failed to copy:', err);
                toast('Failed to copy', 'error');
            });
    };
    
    // Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        function setTheme(mode) {
            if (mode === 'light') {
                document.documentElement.classList.remove('dark');
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                localStorage.setItem('theme', 'light');
            } else {
                document.documentElement.classList.add('dark');
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                localStorage.setItem('theme', 'dark');
            }
        }
        
        themeToggle.addEventListener('click', () => {
            const current = localStorage.getItem('theme') || 'dark';
            setTheme(current === 'dark' ? 'light' : 'dark');
        });
        
        // Initialize theme
        const savedTheme = localStorage.getItem('theme') || 'dark';
        setTheme(savedTheme);
    }
    
    // Form submission helper
    window.submitForm = async function(formElement, options = {}) {
        const form = formElement instanceof HTMLFormElement ? formElement : document.querySelector(formElement);
        if (!form) return;
        
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) setLoading(submitBtn, true, options.loadingText);
        
        try {
            const formData = new FormData(form);
            const response = await fetch(form.action, {
                method: form.method,
                body: formData
            });
            
            if (response.ok) {
                if (options.success) {
                    options.success(response);
                } else if (options.redirect) {
                    window.location.href = options.redirect;
                } else {
                    window.location.reload();
                }
            } else {
                const error = await response.text();
                toast(options.errorMessage || 'Error submitting form', 'error');
                console.error('Form submission error:', error);
            }
        } catch (error) {
            toast('Network error. Please try again.', 'error');
            console.error('Form submission error:', error);
        } finally {
            if (submitBtn) setLoading(submitBtn, false);
        }
    };
    
    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        // Auto-dismiss flash messages after 5 seconds
        setTimeout(() => {
            document.querySelectorAll('.flash-message').forEach(msg => {
                msg.style.opacity = '0';
                setTimeout(() => msg.remove(), 300);
            });
        }, 5000);
        
        // Close flash messages on click
        document.querySelectorAll('.flash-message .close').forEach(btn => {
            btn.addEventListener('click', function() {
                this.closest('.flash-message').remove();
            });
        });
        
        // Initialize tooltips
        document.querySelectorAll('[title]').forEach(el => {
            el.addEventListener('mouseenter', function() {
                const tooltip = document.createElement('div');
                tooltip.className = 'absolute z-50 px-2 py-1 text-xs bg-gray-900 text-white rounded shadow-lg';
                tooltip.textContent = this.title;
                document.body.appendChild(tooltip);
                
                const rect = this.getBoundingClientRect();
                tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
                tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
                
                this._tooltip = tooltip;
            });
            
            el.addEventListener('mouseleave', function() {
                if (this._tooltip) {
                    this._tooltip.remove();
                    delete this._tooltip;
                }
            });
        });
    });
    
    // Export for module usage
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = {
            toast: window.toast,
            showLoading: window.showLoading,
            hideLoading: window.hideLoading,
            confirmAction: window.confirmAction,
            setLoading: window.setLoading,
            copyToClipboard: window.copyToClipboard,
            submitForm: window.submitForm
        };
    }
})();