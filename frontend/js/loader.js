// Loading Bar and Notification Module

const Loader = (() => {
    let loadingBar;
    let progressVal = 0;
    let progressInterval;
    let highlightedNotification = null;
    
    /**
     * Initialize loader on page load
     */
    const init = () => {
        loadingBar = document.getElementById('loading-bar');
        if (!loadingBar) {
            // Create loading bar if doesn't exist
            loadingBar = document.createElement('div');
            loadingBar.id = 'loading-bar';
            loadingBar.className = 'loading-bar';
            document.body.appendChild(loadingBar);
        }
    };
    
    /**
     * Start the loading bar animation
     */
    const start = () => {
        if (!loadingBar) init();
        
        loadingBar.classList.add('active');
        loadingBar.classList.remove('complete', 'fade');
        progressVal = 0;
        loadingBar.style.width = '0%';
        
        // Animate progress
        progressInterval = setInterval(() => {
            if (progressVal < 90) {
                progressVal += Math.random() * 30;
                if (progressVal > 90) progressVal = 90;
                loadingBar.style.width = progressVal + '%';
            }
        }, 300);
    };
    
    /**
     * Complete the loading bar
     */
    const finish = () => {
        clearInterval(progressInterval);
        
        if (!loadingBar) return;
        
        loadingBar.classList.remove('active');
        loadingBar.classList.add('complete');
        loadingBar.style.width = '100%';
        
        // Fade out after delay
        setTimeout(() => {
            loadingBar.classList.add('fade');
        }, 300);
        
        // Reset
        setTimeout(() => {
            progressVal = 0;
            loadingBar.style.width = '0%';
            loadingBar.classList.remove('complete', 'fade');
        }, 600);
    };
    
    /**
     * Show error toast
     */
    const showError = (message) => {
        showToast(message, 'error', 5000);
    };
    
    /**
     * Show success toast
     */
    const showSuccess = (message) => {
        showToast(message, 'success', 3000);
    };
    
    /**
     * Show info toast
     */
    const showInfo = (message) => {
        showToast(message, 'info', 3000);
    };
    
    /**
     * Show warning toast
     */
    const showWarning = (message) => {
        showToast(message, 'warning', 4000);
    };
    
    /**
     * Create and show a toast notification
     */
    const showToast = (message, type = 'info', duration = 3000) => {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        // Icon mapping
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <span class="toast-message">${message}</span>
            <span class="toast-close">✕</span>
        `;
        
        document.body.appendChild(toast);
        
        // Close button handler
        toast.querySelector('.toast-close').addEventListener('click', () => {
            removeToast(toast);
        });
        
        // Auto remove
        const timeoutId = setTimeout(() => {
            removeToast(toast);
        }, duration);
        
        // Store timeout for cleanup
        toast.timeoutId = timeoutId;
        
        return toast;
    };
    
    /**
     * Remove toast with animation
     */
    const removeToast = (toast) => {
        if (toast.timeoutId) clearTimeout(toast.timeoutId);
        toast.classList.add('remove');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    };
    
    /**
     * Show loading overlay
     */
    const showOverlay = (message = 'Loading...') => {
        let overlay = document.getElementById('loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-content">
                    <div class="spinner"></div>
                    <p id="overlay-message">${message}</p>
                </div>
            `;
            document.body.appendChild(overlay);
        } else {
            document.getElementById('overlay-message').textContent = message;
        }
        
        overlay.classList.add('active');
        return overlay;
    };
    
    /**
     * Hide loading overlay
     */
    const hideOverlay = () => {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('active');
        }
    };
    
    /**
     * Create skeleton loading placeholder
     */
    const createSkeleton = (count = 1, type = 'card') => {
        let html = '';
        for (let i = 0; i < count; i++) {
            if (type === 'card') {
                html += `
                    <div class="skeleton-card">
                        <div class="skeleton skeleton-heading"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text"></div>
                        <div class="skeleton skeleton-text"></div>
                    </div>
                `;
            } else if (type === 'row') {
                html += `
                    <div class="skeleton skeleton-text"></div>
                `;
            }
        }
        return html;
    };
    
    return {
        init,
        start,
        finish,
        showError,
        showSuccess,
        showInfo,
        showWarning,
        showToast,
        removeToast,
        showOverlay,
        hideOverlay,
        createSkeleton
    };
})();

// Initialize loader when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', Loader.init);
} else {
    Loader.init();
}
