// UI Module for handling interface interactions

const UI = (() => {
    /**
     * Format currency values
     */
    const formatCurrency = (value) => {
        if (!value && value !== 0) return '-';
        const num = parseFloat(value);
        if (isNaN(num)) return '-';
        
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num);
    };
    
    /**
     * Format large numbers with K, Cr, etc.
     */
    const formatLargeNumber = (value) => {
        if (!value && value !== 0) return '-';
        const num = parseFloat(value);
        if (isNaN(num)) return '-';
        
        const abs = Math.abs(num);
        if (abs >= 10000000) {
            return (num / 10000000).toFixed(2) + ' Cr';
        } else if (abs >= 100000) {
            return (num / 100000).toFixed(2) + ' L';
        } else if (abs >= 1000) {
            return (num / 1000).toFixed(2) + ' K';
        }
        return num.toFixed(2);
    };
    
    /**
     * Format percentage values
     */
    const formatPercent = (value, decimals = 2) => {
        if (!value && value !== 0) return '-';
        const num = parseFloat(value);
        if (isNaN(num)) return '-';
        return num.toFixed(decimals) + '%';
    };
    
    /**
     * Format date
     */
    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        try {
            const date = new Date(dateStr);
            return new Intl.DateTimeFormat('en-IN', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            }).format(date);
        } catch {
            return dateStr;
        }
    };
    
    /**
     * Get price change badge (for positive/negative values)
     */
    const getPriceChangeBadge = (value) => {
        if (!value && value !== 0) return '';
        const num = parseFloat(value);
        const isPositive = num >= 0;
        const icon = isPositive ? '▲' : '▼';
        const color = isPositive ? 'success' : 'danger';
        
        return `<span class="badge badge-${color}">${icon} ${Math.abs(num).toFixed(2)}</span>`;
    };
    
    /**
     * Highlight text in search results
     */
    const highlightText = (text, query) => {
        if (!query) return text;
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    };
    
    /**
     * Debounce function for search inputs
     */
    const debounce = (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    };
    
    /**
     * Throttle function for scroll events
     */
    const throttle = (func, limit) => {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    };
    
    /**
     * Show/hide tab content
     */
    const switchTab = (tabName) => {
        // Hide all tab contents
        const contents = document.querySelectorAll('.tab-content');
        contents.forEach(content => content.classList.remove('active'));
        
        // Remove active class from all tabs
        const tabs = document.querySelectorAll('.nav-tab');
        tabs.forEach(tab => tab.classList.remove('active'));
        
        // Show selected tab content
        const selectedContent = document.getElementById(`tab-${tabName}`);
        if (selectedContent) {
            selectedContent.classList.add('active');
        }
        
        // Mark selected tab as active
        const selectedTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (selectedTab) {
            selectedTab.classList.add('active');
        }
    };
    
    /**
     * Create a metric card HTML
     */
    const createMetricCard = (label, value, change = null) => {
        let changeHtml = '';
        if (change !== null) {
            const isPositive = change >= 0;
            const icon = isPositive ? '▲' : '▼';
            const color = isPositive ? 'success' : 'danger';
            changeHtml = `<div class="metric-change ${color}">${icon} ${Math.abs(change).toFixed(2)}%</div>`;
        }
        
        return `
            <div class="metric-card">
                <div class="metric-label">${label}</div>
                <div class="metric-value">${value}</div>
                ${changeHtml}
            </div>
        `;
    };
    
    /**
     * Create a stat item HTML
     */
    const createStatItem = (label, value) => {
        return `
            <div class="stat-item">
                <div class="stat-label">${label}</div>
                <div class="stat-value">${value}</div>
            </div>
        `;
    };
    
    /**
     * Create table row HTML
     */
    const createTableRow = (data) => {
        let html = '<tr>';
        Object.values(data).forEach(value => {
            html += `<td>${value}</td>`;
        });
        html += '</tr>';
        return html;
    };
    
    /**
     * Create empty state HTML
     */
    const createEmptyState = (icon = '📊', title = 'No Data', description = '') => {
        return `
            <div class="empty-state">
                <div class="empty-state-icon">${icon}</div>
                <div class="empty-state-title">${title}</div>
                <div class="empty-state-description">${description}</div>
            </div>
        `;
    };
    
    /**
     * Smooth scroll to element
     */
    const scrollToElement = (selector, offset = 0) => {
        const element = document.querySelector(selector);
        if (element) {
            const top = element.getBoundingClientRect().top + window.scrollY - offset;
            window.scrollTo({
                top: top,
                behavior: 'smooth'
            });
        }
    };
    
    /**
     * Copy text to clipboard
     */
    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text).then(() => {
            Loader.showSuccess('Copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy:', err);
            Loader.showError('Failed to copy to clipboard');
        });
    };
    
    /**
     * Format large data table for responsiveness
     */
    const makeTableResponsive = (tableSelector) => {
        const table = document.querySelector(tableSelector);
        if (!table) return;
        
        const rows = table.querySelectorAll('tbody tr');
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent);
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                cell.setAttribute('data-label', headers[index]);
            });
        });
    };
    
    return {
        formatCurrency,
        formatLargeNumber,
        formatPercent,
        formatDate,
        getPriceChangeBadge,
        highlightText,
        debounce,
        throttle,
        switchTab,
        createMetricCard,
        createStatItem,
        createTableRow,
        createEmptyState,
        scrollToElement,
        copyToClipboard,
        makeTableResponsive
    };
})();
