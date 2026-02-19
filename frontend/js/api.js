// API Module for handling all backend requests

const API = (() => {
    const BASE_URL = 'http://localhost:5000/api';
    
    // Timeout for requests (ms)
    const REQUEST_TIMEOUT = 30000;
    
    // Abort controller for managing requests
    let abortController = new AbortController();
    
    /**
     * Make a GET request with loading bar
     * @param {string} endpoint - API endpoint
     * @param {object} params - Query parameters
     * @returns {Promise}
     */
    const get = async (endpoint, params = {}) => {
        try {
            // Start loading bar
            Loader.start();
            
            // Build query string
            const queryString = new URLSearchParams(params).toString();
            const url = queryString ? `${BASE_URL}${endpoint}?${queryString}` : `${BASE_URL}${endpoint}`;
            
            // Set timeout
            const timeoutId = setTimeout(() => abortController.abort(), REQUEST_TIMEOUT);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                signal: abortController.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            Loader.finish();
            return data;
            
        } catch (error) {
            Loader.finish();
            if (error.name !== 'AbortError') {
                console.error(`API Error: ${endpoint}`, error);
                Loader.showError(`Failed to load data: ${error.message}`);
            }
            throw error;
        }
    };
    
    /**
     * Make a POST request
     * @param {string} endpoint - API endpoint
     * @param {object} data - Request body
     * @returns {Promise}
     */
    const post = async (endpoint, data = {}) => {
        try {
            Loader.start();
            
            const timeoutId = setTimeout(() => abortController.abort(), REQUEST_TIMEOUT);
            
            const response = await fetch(`${BASE_URL}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data),
                signal: abortController.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            Loader.finish();
            return result;
            
        } catch (error) {
            Loader.finish();
            if (error.name !== 'AbortError') {
                console.error(`API Error: ${endpoint}`, error);
                Loader.showError(`Failed to send request: ${error.message}`);
            }
            throw error;
        }
    };
    
    /**
     * Cancel all pending requests
     */
    const cancel = () => {
        abortController.abort();
        abortController = new AbortController();
    };
    
    return {
        // Public methods
        get,
        post,
        cancel,
        
        // Nifty 50 Companies
        getNifty50: () => get('/nifty50'),
        
        // Company Info
        getCompanyInfo: (symbol) => get('/company/info', { symbol }),
        
        // Stock History
        getStockHistory: (symbol, start, end) => 
            get('/company/history', { symbol, start, end }),
        
        // Financial Metrics
        getFinancials: (symbol) => get('/company/financials', { symbol }),
        
        // News and Analysis
        getNewsAnalysis: (symbol) => get('/news/analyze-full', { symbol })
    };
})();
