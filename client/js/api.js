const API_BASE_URL = '/api';

const api = {
    async getNifty50() {
        try {
            const response = await fetch(`${API_BASE_URL}/nifty50`);
            return await response.json();
        } catch (error) {
            console.error('Error fetching Nifty 50:', error);
            return [];
        }
    },

    async getCompanyInfo(symbol) {
        try {
            const response = await fetch(`${API_BASE_URL}/company/info?symbol=${symbol}`);
            return await response.json();
        } catch (error) {
            console.error(`Error fetching info for ${symbol}:`, error);
            return null;
        }
    },

    async getCompanyFinancials(symbol) {
        try {
            const response = await fetch(`${API_BASE_URL}/company/financials?symbol=${symbol}`);
            if (!response.ok) {
                console.warn(`Financials API returned ${response.status} for ${symbol}`);
                return {};
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching financials for ${symbol}:`, error);
            return {};
        }
    },

    async getStockHistory(symbol, start, end) {
        try {
            const response = await fetch(`${API_BASE_URL}/company/history?symbol=${symbol}&start=${start}&end=${end}`);
            if (!response.ok) {
                console.warn(`History API returned ${response.status} for ${symbol}`);
                return [];
            }
            const data = await response.json();
            return Array.isArray(data) ? data : [];
        } catch (error) {
            console.error(`Error fetching history for ${symbol}:`, error);
            return [];
        }
    },

    async getNewsAnalysis(symbol) {
        try {
            const response = await fetch(`${API_BASE_URL}/company/search?symbol=${symbol}`);
            if (!response.ok) {
                console.warn(`News API returned ${response.status} for ${symbol}`);
                return { data: [] };
            }
            const data = await response.json();
            // Ensure we always return an object with 'data' property
            return data && data.data ? data : { data: [] };
        } catch (error) {
            console.error(`Error fetching news analysis for ${symbol}:`, error);
            return { data: [] };
        }
    }
};

export default api;
