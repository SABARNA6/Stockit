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
            return await response.json();
        } catch (error) {
            console.error(`Error fetching financials for ${symbol}:`, error);
            return null;
        }
    },

    async getStockHistory(symbol, start, end) {
        try {
            const response = await fetch(`${API_BASE_URL}/company/history?symbol=${symbol}&start=${start}&end=${end}`);
            return await response.json();
        } catch (error) {
            console.error(`Error fetching history for ${symbol}:`, error);
            return [];
        }
    },

    async getNewsAnalysis(symbol) {
        try {
            const response = await fetch(`${API_BASE_URL}/news/analyze-full?symbol=${symbol}`);
            return await response.json();
        } catch (error) {
            console.error(`Error fetching news analysis for ${symbol}:`, error);
            return null;
        }
    }
};

export default api;
