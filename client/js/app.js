import api from './api.js';

// State Management
let currentSymbol = '';
let nifty50 = [];
let priceChart = null;
let currentHistory = [];
let newsData = null;

// DOM Elements
const searchInput = document.getElementById('stock-search');
const searchResults = document.getElementById('search-results');
const companyHeader = document.getElementById('company-header');
const metricsSection = document.getElementById('metrics-section');
const chartSection = document.getElementById('chart-section');
const volumeSection = document.getElementById('volume-section');
const aboutSection = document.getElementById('about-section');
const summarySection = document.getElementById('summary-section');
const financialsSection = document.getElementById('financials-section');
const historySection = document.getElementById('history-section');
const strategySection = document.getElementById('strategy-section');
const newsSection = document.getElementById('news-section');
const loader = document.getElementById('loader');
const emptyState = document.getElementById('empty-state');

// Dynamic Elements
const companyName = document.getElementById('company-name');
const companySymbol = document.getElementById('company-symbol');
const currentPrice = document.getElementById('current-price');
const companySummary = document.getElementById('company-summary');
const newsList = document.getElementById('news-list');
const sentimentSummary = document.getElementById('sentiment-summary');
const shortTermList = document.getElementById('short-term-strategy');
const swingList = document.getElementById('swing-strategy');
const longTermList = document.getElementById('long-term-strategy');
const outlookBadge = document.getElementById('outlook-badge');
const financialsTableBody = document.getElementById('financials-table-body');
const historyTableBody = document.getElementById('history-table-body');
const candleChartContainer = document.getElementById('candleChart');
const volumeChartContainer = document.getElementById('volumeChart');
const volumeStrikeBadge = document.getElementById('volume-strike-badge');
const dynamicSummary = document.getElementById('dynamic-summary');

// Initialization
document.addEventListener('DOMContentLoaded', async () => {
    nifty50 = await api.getNifty50();
    setupSearch();
    setupEventListeners();
});

function setupSearch() {
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toUpperCase();
        if (query.length < 1) {
            searchResults.classList.add('hidden');
            return;
        }

        const filtered = nifty50.filter(stock =>
            stock.Symbol.includes(query) ||
            (stock["Company Name"] && stock["Company Name"].toUpperCase().includes(query))
        ).slice(0, 10);

        if (filtered.length > 0) {
            searchResults.innerHTML = filtered.map(stock => `
                <div class="search-item" data-symbol="${stock.Symbol}">
                    <span class="symbol">${stock.Symbol}</span>
                    <span class="name">${stock["Company Name"]}</span>
                </div>
            `).join('');
            searchResults.classList.remove('hidden');
        } else {
            searchResults.classList.add('hidden');
        }
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add('hidden');
        }
    });

    searchResults.addEventListener('click', (e) => {
        const item = e.target.closest('.search-item');
        if (item) {
            const symbol = item.dataset.symbol;
            selectCompany(symbol);
            searchResults.classList.add('hidden');
            searchInput.value = symbol;
        }
    });
}

function setupEventListeners() {
    document.querySelectorAll('.tag-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            selectCompany(btn.textContent.trim());
            searchInput.value = btn.textContent.trim();
        });
    });

    document.querySelectorAll('.chart-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.chart-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            updateChartPeriod(btn.dataset.period);
        });
    });

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const type = btn.dataset.type;
            const lineView = document.getElementById('line-chart-view');
            const candleView = document.getElementById('candle-chart-view');

            if (type === 'line') {
                lineView.classList.remove('hidden');
                candleView.classList.add('hidden');
            } else {
                candleView.classList.remove('hidden');
                lineView.classList.add('hidden');
                renderCandleChart(currentHistory);
            }
        });
    });
}

async function selectCompany(symbol) {
    currentSymbol = symbol;
    showLoader();
    hideSections();

    try {
        const [info, financials, newsAnalysis] = await Promise.all([
            api.getCompanyInfo(symbol),
            api.getCompanyFinancials(symbol),
            api.getNewsAnalysis(symbol)
        ]);

        if (info && !info.error) {
            newsData = newsAnalysis;
            renderCompanyInfo(info);
            renderMetrics(info, financials);
            renderAbout(info);
            renderNews(newsAnalysis);
            renderFinancialsTable(financials);

            await fetchAndRenderChart('1Y');
            renderStrategy(currentHistory, newsAnalysis);
            renderVolumeChart(currentHistory);
            renderHistoryTable(currentHistory);
            renderAnalysisSummary(currentHistory, newsAnalysis);

            showSections();
        } else {
            alert('Failed to fetch data for this symbol.');
            showEmptyState();
        }
    } catch (error) {
        console.error('Error during selection:', error);
        showEmptyState();
    } finally {
        hideLoader();
    }
}

function renderCompanyInfo(info) {
    companyName.textContent = info["Company Name"];
    companySymbol.textContent = `NSE: ${info.Symbol}`;
    currentPrice.textContent = info.Price ? info.Price.toLocaleString('en-IN') : 'N/A';
}

function renderMetrics(info, financials) {
    const metrics = [
        { label: 'Market Cap', value: info.marketCap ? `₹ ${(info.marketCap / 10000000).toFixed(2)} Cr` : 'N/A' },
        { label: 'Current Price', value: info.Price ? `₹ ${info.Price}` : 'N/A' },
        { label: 'Revenue', value: financials.Revenue ? `₹ ${(financials.Revenue / 10000000).toFixed(2)} Cr` : 'N/A' },
        { label: 'Net Profit', value: financials["Net Profit"] ? `₹ ${(financials["Net Profit"] / 10000000).toFixed(2)} Cr` : 'N/A' },
        { label: 'EBITDA Margin', value: financials["EBITDA Margin"] ? `${financials["EBITDA Margin"].toFixed(2)}%` : 'N/A' }
    ];

    metricsSection.innerHTML = metrics.map(m => `
        <div class="metric-item">
            <span class="metric-label">${m.label}</span>
            <span class="metric-value">${m.value}</span>
        </div>
    `).join('');
}

function renderFinancialsTable(financials) {
    financialsTableBody.innerHTML = Object.entries(financials).map(([key, value]) => {
        if (value === null || value === undefined) return '';
        let displayValue = typeof value === 'number' ?
            (value > 10000000 ? (value / 10000000).toFixed(2) + ' Cr' : value.toLocaleString('en-IN')) : value;

        return `
            <tr>
                <td><strong>${key}</strong></td>
                <td>${displayValue}</td>
            </tr>
        `;
    }).join('');
}

function renderAbout(info) {
    companySummary.textContent = info["Short Summary"] || 'No summary available.';
}

function renderNews(newsAnalysis) {
    if (!newsAnalysis || !newsAnalysis.news) {
        newsList.innerHTML = '<p>No news found for this company.</p>';
        sentimentSummary.innerHTML = '';
        return;
    }

    const overall = newsAnalysis.analysis?.overall_sentiment || 'Neutral';
    sentimentSummary.innerHTML = `
        <span class="news-sentiment sentiment-${overall.toLowerCase()}">
            Overall: ${overall}
        </span>
    `;

    newsList.innerHTML = newsAnalysis.news.map((item, index) => {
        const analysis = newsAnalysis.analysis?.details?.[index] || {};
        const sentiment = analysis.sentiment || 'Neutral';

        return `
            <div class="news-item">
                <a href="${item.link || '#'}" target="_blank" class="news-title">${item.title}</a>
                <div class="news-meta">
                    <span>${new Date(item.publisher?.publishTime || Date.now()).toLocaleDateString()}</span>
                    <span>${item.publisher || 'Finance News'}</span>
                    <span class="news-sentiment sentiment-${sentiment.toLowerCase()}">${sentiment}</span>
                </div>
            </div>
        `;
    }).join('');
}

function renderStrategy(history, newsAnalysis) {
    if (!history || history.length < 2) return;

    const firstPrice = history[0].Close;
    const lastPrice = history[history.length - 1].Close;
    const priceChange = ((lastPrice - firstPrice) / firstPrice) * 100;
    const trend = priceChange > 5 ? 'uptrend' : (priceChange < -5 ? 'downtrend' : 'sideways');

    const sentiment = newsAnalysis?.analysis?.overall_sentiment?.toLowerCase() || 'neutral';

    let outlook = 'Neutral';
    let shortTerm = [], swing = [], longTerm = [];

    if (trend === 'uptrend' && sentiment === 'positive') {
        outlook = 'Strong Bullish';
        shortTerm = ['Momentum is strong; look for continuation.', 'Set tight stop-loss below breakout level.', 'Target 2-3% in 3 days.'];
        swing = ['Buy on minor dips.', 'Positive sentiment favors holding for weeks.', 'Target 10% upside.'];
        longTerm = ['Great time for SIP accumulation.', 'Fundamentals supported by positive news.', 'Strong hold.'];
    } else if (trend === 'downtrend' && sentiment === 'negative') {
        outlook = 'Strong Bearish';
        shortTerm = ['Avoid long positions.', 'Watch for further breakdown.', 'Strict exit if holding.'];
        swing = ['Wait for signs of reversal.', 'High volatility expected.', 'Stay on sidelines.'];
        longTerm = ['Evaluate long-term thesis.', 'Keep cash ready for bottom fishing.', 'Wait for stabilization.'];
    } else {
        outlook = 'Neutral / Mixed';
        shortTerm = ['Range bound trading.', 'Buy near support, sell near resistance.', 'Wait for breakout.'];
        swing = ['Mixed signals; reduce position sizes.', 'Monitor news catalysts.', 'Neutral stance.'];
        longTerm = ['Maintain existing positions.', 'Continue systematic investing.', 'Quality focus remains key.'];
    }

    shortTermList.innerHTML = shortTerm.map(s => `<li>${s}</li>`).join('');
    swingList.innerHTML = swing.map(s => `<li>${s}</li>`).join('');
    longTermList.innerHTML = longTerm.map(s => `<li>${s}</li>`).join('');

    const badgeClass = outlook.includes('Bullish') ? 'sentiment-positive' : (outlook.includes('Bearish') ? 'sentiment-negative' : 'sentiment-neutral');
    outlookBadge.innerHTML = `<span class="outlook-badge ${badgeClass}">${outlook}</span>`;
}

function renderAnalysisSummary(history, newsAnalysis) {
    if (!history || history.length < 2) return;

    const firstPrice = history[0].Close;
    const lastPrice = history[history.length - 1].Close;
    const priceChange = ((lastPrice - firstPrice) / firstPrice) * 100;
    const avgVolume = history.reduce((a, b) => a + b.Volume, 0) / history.length;
    const maxVolume = Math.max(...history.map(d => d.Volume));
    const volumeSpike = maxVolume > avgVolume * 1.5;

    const sentiment = newsAnalysis?.analysis?.overall_sentiment || 'Neutral';

    dynamicSummary.innerHTML = `
        <p style="margin-bottom: 12px;"><strong>📊 Performance:</strong> The stock has delivered a <strong>${priceChange.toFixed(2)}%</strong> return over the selected period. 
        The current price trend is considered <strong>${priceChange > 5 ? 'Bullish' : (priceChange < -5 ? 'Bearish' : 'Sideways')}</strong>.</p>
        
        <p style="margin-bottom: 12px;"><strong>💹 Volume Insight:</strong> ${volumeSpike ? '⚠️ A significant <strong>Volume Spike</strong> was detected during this period, indicating high institutional or retail interest.' : 'Trading volumes have remained relatively <strong>stable</strong> without major spikes.'}</p>
        
        <p><strong>📰 Sentiment Analysis:</strong> The news cycle for ${currentSymbol} is currently <strong>${sentiment}</strong>, which ${sentiment === 'Positive' ? 'supports the upward momentum' : (sentiment === 'Negative' ? 'may act as a headwind' : 'suggests a wait-and-watch approach')}.</p>
    `;
}

async function fetchAndRenderChart(period) {
    let days = 365;
    if (period === '6M') days = 180;
    if (period === '3M') days = 90;
    if (period === '1M') days = 30;

    const endDate = new Date().toISOString().split('T')[0];
    const startDate = new Date(Date.now() - (days * 24 * 60 * 60 * 1000)).toISOString().split('T')[0];

    currentHistory = await api.getStockHistory(currentSymbol, startDate, endDate);
    renderPriceChart();

    // Auto-update other history-dependent views
    if (!document.getElementById('candle-chart-view').classList.contains('hidden')) {
        renderCandleChart(currentHistory);
    }
    renderVolumeChart(currentHistory);
    renderHistoryTable(currentHistory);
}

function renderPriceChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');
    if (priceChart) priceChart.destroy();
    if (!currentHistory || currentHistory.length === 0) return;

    const labels = currentHistory.map(d => d.Date);
    const prices = currentHistory.map(d => d.Close);

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Close Price',
                data: prices,
                borderColor: '#3182ce',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                backgroundColor: 'rgba(49, 130, 206, 0.05)',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: 'index' },
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { maxTicksLimit: 10, color: '#718096' } },
                y: { grid: { color: '#f1f5f9' }, ticks: { color: '#718096', callback: v => '₹' + v.toLocaleString('en-IN') } }
            }
        }
    });
}

function renderCandleChart(data) {
    if (!data || data.length === 0) return;

    const displayData = data.length > 20 ? data.slice(-20) : data;
    const allPrices = displayData.flatMap(d => [d.High, d.Low]);
    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const range = max - min;

    candleChartContainer.innerHTML = displayData.map(d => {
        const isBullish = d.Close >= d.Open;
        const color = isBullish ? 'var(--success-color)' : 'var(--danger-color)';

        const wickTop = ((max - d.High) / range) * 350;
        const wickHeight = ((d.High - d.Low) / range) * 350;
        const bodyTop = ((max - Math.max(d.Open, d.Close)) / range) * 350;
        const bodyHeight = Math.max((Math.abs(d.Close - d.Open) / range) * 350, 4);

        return `
            <div class="candle">
                <div style="height: ${wickTop}px;"></div>
                <div class="candle-wick" style="height: ${wickHeight}px; position: relative;">
                    <div class="candle-body" style="position: absolute; top: ${bodyTop - wickTop}px; left: -5px; height: ${bodyHeight}px; background: ${color};"></div>
                </div>
                <div class="candle-label">${d.Date.split('-')[2]}/${d.Date.split('-')[1]}</div>
            </div>
        `;
    }).join('');
}

function renderVolumeChart(data) {
    if (!data || data.length === 0) return;

    const displayData = data.length > 15 ? data.slice(-15) : data;
    const volumes = displayData.map(d => d.Volume);
    const maxVol = Math.max(...volumes);
    const avgVol = data.reduce((a, b) => a + b.Volume, 0) / data.length;

    const isStrike = data[data.length - 1].Volume > avgVol * 1.5;
    volumeStrikeBadge.innerHTML = isStrike ? '<span class="outlook-badge sentiment-neutral">⚠️ VOLUME SPIKE</span>' : '';

    volumeChartContainer.innerHTML = displayData.map(d => {
        const height = (d.Volume / maxVol) * 120;
        const color = d.Volume > avgVol * 1.5 ? 'var(--warning-color)' : 'var(--accent-color)';

        return `
            <div class="bar-wrapper">
                <div class="bar-value" style="color: ${color}">${(d.Volume / 100000).toFixed(1)}L</div>
                <div class="bar" style="height: ${height}px; background: ${color}; opacity: 0.7;"></div>
                <div class="bar-label">${d.Date.split('-')[2]}/${d.Date.split('-')[1]}</div>
            </div>
        `;
    }).join('');
}

function renderHistoryTable(data) {
    const reversed = [...data].reverse().slice(0, 10);
    historyTableBody.innerHTML = reversed.map((d, i) => {
        const prev = reversed[i + 1] || d;
        const chg = ((d.Close - prev.Close) / prev.Close) * 100;
        const chgClass = chg >= 0 ? 'positive' : 'negative';

        return `
            <tr>
                <td>${d.Date}</td>
                <td>₹${d.Open.toLocaleString()}</td>
                <td>₹${d.High.toLocaleString()}</td>
                <td>₹${d.Low.toLocaleString()}</td>
                <td>₹${d.Close.toLocaleString()}</td>
                <td>${(d.Volume / 100000).toFixed(1)}L</td>
                <td class="${chgClass}">${chg >= 0 ? '+' : ''}${chg.toFixed(2)}%</td>
            </tr>
        `;
    }).join('');
}

function updateChartPeriod(period) {
    fetchAndRenderChart(period);
}

// UI Helpers
function showLoader() { loader.style.display = 'flex'; }
function hideLoader() { loader.style.display = 'none'; }
function showEmptyState() { emptyState.style.display = 'block'; }
function hideEmptyState() { emptyState.style.display = 'none'; }

function showSections() {
    [companyHeader, metricsSection, chartSection, volumeSection, aboutSection, summarySection, financialsSection, historySection, strategySection, newsSection].forEach(s => s.classList.remove('hidden'));
    hideEmptyState();
}

function hideSections() {
    [companyHeader, metricsSection, chartSection, volumeSection, aboutSection, summarySection, financialsSection, historySection, strategySection, newsSection].forEach(s => s.classList.add('hidden'));
}
