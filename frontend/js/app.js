// Main Application Module

const App = (() => {
    let currentSymbol = null;
    let currentData = {};

    /**
     * Initialize the application
     */
    const init = async () => {
        setupEventListeners();

        // Check if symbol is in URL params
        const params = new URLSearchParams(window.location.search);
        const symbol = params.get('symbol');

        if (symbol) {
            loadCompanyData(symbol);
        } else {
            showWelcome();
        }
    };

    /**
     * Setup all event listeners
     */
    const setupEventListeners = () => {
        // Search functionality
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', UI.debounce(handleSearch, 300));
        }

        // Navigation tabs
        const navTabs = document.querySelectorAll('.nav-tab');
        navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.getAttribute('data-tab');
                UI.switchTab(tabName);
            });
        });

        // Search form
        const searchForm = document.querySelector('.search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', handleSearchSubmit);
        }
    };

    /**
     * Handle search input
     */
    const handleSearch = (event) => {
        const query = event.target.value.trim().toLowerCase();
        if (!query || query.length < 1) return;

        // Could add autocomplete here
        console.log('Searching for:', query);
    };

    /**
     * Handle search form submission
     */
    const handleSearchSubmit = (event) => {
        event.preventDefault();
        const input = event.target.querySelector('input');
        const symbol = input.value.trim().toUpperCase();

        if (symbol) {
            loadCompanyData(symbol);
            window.history.pushState(null, '', `?symbol=${symbol}`);
        }
    };

    /**
     * Load company data
     */
    const loadCompanyData = async (symbol) => {
        try {
            currentSymbol = symbol;
            Loader.start();

            // Fetch company info
            const info = await API.getCompanyInfo(symbol);
            currentData.info = info;

            renderCompanyHeader(info);
            renderOverviewTab();

            // Fetch additional data
            loadAllTabs();

        } catch (error) {
            Loader.showError(`Failed to load data for ${symbol}`);
            console.error('Error loading company data:', error);
        }
    };

    /**
     * Load all analysis tabs
     */
    const loadAllTabs = async () => {
        try {
            // Load chart data
            loadChartTab();

            // Load analysis data
            loadAnalysisTab();

            // Load financials
            loadFinancialsTab();

            // Load news
            loadNewsTab();

        } catch (error) {
            console.error('Error loading tabs:', error);
        }
    };

    /**
     * Render company header
     */
    const renderCompanyHeader = (info) => {
        const headerContainer = document.getElementById('company-header-container');
        if (!headerContainer) return;

        const companyName = info['Company Name'] || info['longName'] || 'Unknown Company';
        const symbol = info['Symbol'] || currentSymbol;
        const price = info['Price'] || 0;
        const priceHtml = UI.formatCurrency(price);

        headerContainer.innerHTML = `
            <div class="company-header">
                <div class="company-title">
                    <div class="company-icon">📊</div>
                    <div class="company-info">
                        <h1>${companyName}</h1>
                        <div class="company-symbol">${symbol}</div>
                        <div class="company-industry">Financial Services</div>
                    </div>
                </div>
                <div class="stock-price">
                    <div class="price-value">${priceHtml}</div>
                    <div class="price-change positive">▲ 2.5%</div>
                </div>
            </div>
        `;
    };

    /**
     * Render overview tab
     */
    const renderOverviewTab = () => {
        const tabContent = document.getElementById('tab-overview');
        if (!tabContent) return;

        const info = currentData.info || {};

        let html = `
            <div class="section">
                <h3 class="section-title">📈 Key Metrics</h3>
                <div class="stats-row">
                    ${UI.createStatItem('P/E Ratio', info['trailingPE'] ? info['trailingPE'].toFixed(2) : '-')}
                    ${UI.createStatItem('Market Cap', UI.formatLargeNumber(info['marketCap']))}
                    ${UI.createStatItem('52W High', UI.formatCurrency(info['fiftyTwoWeekHigh']))}
                    ${UI.createStatItem('52W Low', UI.formatCurrency(info['fiftyTwoWeekLow']))}
                </div>
            </div>
        `;

        const summary = info['longBusinessSummary'] || 'No description available';
        html += `
            <div class="section">
                <h3 class="section-title">📝 About Company</h3>
                <div class="card">
                    <div class="card-body">
                        <p>${summary}</p>
                    </div>
                </div>
            </div>
        `;

        tabContent.innerHTML = html;
    };

    /**
     * Load chart tab
     */
    const loadChartTab = async () => {
        const tabContent = document.getElementById('tab-chart');
        if (!tabContent) return;

        try {
            const endDate = new Date().toISOString().split('T')[0];
            const startDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

            // For now, show placeholder
            if (!currentSymbol) return;

            // In a real implementation, you'd fetch historical data and render a chart
            // For now, we'll just show a card
            tabContent.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <div class="card-header-title">
                            <div class="card-header-icon">📊</div>
                            <h3>Price Chart (90 Days)</h3>
                        </div>
                    </div>
                    <div class="card-body">
                        <p class="text-secondary">Chart visualization would be rendered here using Chart.js or similar library</p>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Error loading chart:', error);
        }
    };

    /**
     * Load analysis tab
     */
    const loadAnalysisTab = async () => {
        const tabContent = document.getElementById('tab-analysis');
        if (!tabContent) return;

        try {
            Loader.showOverlay('Analyzing financial data...');

            const analysis = await API.getFinancials(currentSymbol);
            Loader.hideOverlay();

            if (!analysis || Object.keys(analysis).length === 0) {
                tabContent.innerHTML = UI.createEmptyState('📊', 'No Analysis Data', 'Financial data not available');
                return;
            }

            let html = '<div class="section">';
            html += '<h3 class="section-title">💹 Financial Analysis</h3>';
            html += '<div class="stats-row">';

            for (const [key, value] of Object.entries(analysis).slice(0, 8)) {
                html += UI.createMetricCard(key, UI.formatLargeNumber(value));
            }

            html += '</div></div>';
            tabContent.innerHTML = html;

        } catch (error) {
            console.error('Error loading analysis:', error);
            const tabContent = document.getElementById('tab-analysis');
            if (tabContent) {
                tabContent.innerHTML = UI.createEmptyState('❌', 'Error Loading Analysis', error.message);
            }
        }
    };

    /**
     * Load financials tab
     */
    const loadFinancialsTab = async () => {
        const tabContent = document.getElementById('tab-financials');
        if (!tabContent) return;

        try {
            const financials = await API.getFinancials(currentSymbol);

            if (!financials || Object.keys(financials).length === 0) {
                tabContent.innerHTML = UI.createEmptyState('📊', 'No Financial Data', 'Data not available');
                return;
            }

            let html = `
                <div class="section">
                    <h3 class="section-title">📊 Financial Data</h3>
                    <div class="card">
                        <table class="data-grid">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Value</th>
                                </tr>
                            </thead>
                            <tbody>
            `;

            for (const [key, value] of Object.entries(financials)) {
                html += `<tr><td>${key}</td><td>${UI.formatLargeNumber(value)}</td></tr>`;
            }

            html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            tabContent.innerHTML = html;

        } catch (error) {
            console.error('Error loading financials:', error);
        }
    };

    /**
     * Load news tab
     */
    const loadNewsTab = async () => {
        const tabContent = document.getElementById('tab-news');
        if (!tabContent) return;

        try {
            Loader.showOverlay('Fetching news with sentiment analysis...');

            const news = await API.getNewsAnalysis(currentSymbol);
            Loader.hideOverlay();

            if (!news || Object.keys(news).length === 0) {
                tabContent.innerHTML = UI.createEmptyState('📰', 'No News Available', 'There are no recent news articles available');
                return;
            }

            let html = '<div class="section">';
            html += '<h3 class="section-title">📰 News & Sentiment Analysis</h3>';
            html += '<div class="grid grid-cols-1 gap-3">';

            // Render news items
            if (typeof news === 'object') {
                for (const [key, value] of Object.entries(news).slice(0, 10)) {
                    const sentiment = typeof value === 'object' ? value.sentiment : value;
                    const color = sentiment > 0.5 ? 'success' : sentiment < -0.5 ? 'danger' : 'warning';
                    console.log(sentiment);
                    html += `
                        <div class="card">
                            <div class="card-body">
                                <h4 id="${key}">${value.headline}</h4>
                                <p class="text-secondary text-small">Sentiment: <span class="badge badge-${color}">${(sentiment * 100).toFixed(0)}%</span></p>
                            </div>
                        </div>
                    `;
                }
            }

            html += '</div></div>';
            tabContent.innerHTML = html;

        } catch (error) {
            console.error('Error loading news:', error);
            const tabContent = document.getElementById('tab-news');
            if (tabContent) {
                tabContent.innerHTML = UI.createEmptyState('⚠️', 'Error Loading News', error.message);
            }
        }
    };

    /**
     * Show welcome screen
     */
    const showWelcome = () => {
        const mainContent = document.getElementById('main-content');
        if (mainContent) {
            mainContent.innerHTML = `
                <div class="empty-state" style="margin-top: 100px;">
                    <div class="empty-state-icon" style="font-size: 72px;">📈</div>
                    <div class="empty-state-title">Stock Intelligence Platform</div>
                    <div class="empty-state-description">
                        Search for a stock symbol to view detailed analysis, financial metrics, and market insights
                    </div>
                    <div style="margin-top: 24px;">
                        <input 
                            type="text" 
                            id="welcome-search" 
                            placeholder="Enter symbol (e.g., TCS, RELIANCE)" 
                            style="
                                padding: 12px 16px;
                                background: var(--tertiary-bg);
                                border: 1px solid var(--border-color);
                                border-radius: 6px;
                                color: var(--text-primary);
                                width: 300px;
                                max-width: 100%;
                            "
                        />
                    </div>
                </div>
            `;

            const welcomeSearch = document.getElementById('welcome-search');
            if (welcomeSearch) {
                welcomeSearch.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        const symbol = welcomeSearch.value.trim().toUpperCase();
                        if (symbol) {
                            loadCompanyData(symbol);
                            window.history.pushState(null, '', `?symbol=${symbol}`);
                        }
                    }
                });
            }
        }
    };

    return {
        init,
        loadCompanyData,
        currentSymbol: () => currentSymbol
    };
})();

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', App.init);
} else {
    App.init();
}
