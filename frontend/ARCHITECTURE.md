# Stockit Frontend - Structured Architecture

## 📁 Folder Structure

```
frontend/
│
├── index.html                  # Main application entry point
├── server.py                   # Development server (Flask)
│
├── css/                        # Stylesheets (modular, easy to debug)
│   ├── main.css              # Core styles (colors, typography, utilities)
│   ├── navbar.css            # Header & navigation bar styles
│   ├── cards.css             # Card components & data grid styles
│   └── loading.css           # Loading bars, spinners, toast notifications
│
├── js/                        # JavaScript modules (modular architecture)
│   ├── loader.js             # Loading bar & notification system
│   ├── ui.js                 # UI utilities (formatting, DOM helpers)
│   ├── api.js                # API calls & data fetching
│   └── app.js                # Main application logic & controllers
│
└── components/               # Reusable components (future use)
    └── (component folders can be added here)
```

## 🎨 Modern UI Features

### 1. **Screener.in-Inspired Design**
- Clean, professional layout with dark theme
- Structured data presentation with cards and tables
- Company header with key metrics
- Navigation tabs for different analysis sections

### 2. **Navigation Sections**
The UI includes the following navigation tabs:
- 📊 **Overview** - Company info & key metrics
- 📈 **Chart** - Price charts (extensible for Chart.js)
- 💹 **Analysis** - Financial analysis based on sentiment
- 💰 **Financials** - Detailed financial statements
- 👥 **Peers** - Peer company comparison
- 📰 **News & Sentiment** - AI-powered sentiment analysis with FinBERT
- 📄 **Documents** - Company documents & announcements

### 3. **Loading Indicators**
- **Progress Bar** - Smooth animated top loading bar with multiple states
- **Toast Notifications** - Success, error, warning, info messages
- **Loading Overlay** - Full-screen loader with spinner for long operations
- **Skeleton Loading** - Placeholder cards while data loads

## 🔧 Technical Stack

### Backend Integration
```javascript
API_BASE_URL = 'http://localhost:5000/api'

Available Endpoints:
- /api/nifty50                      # Get Nifty 50 companies
- /api/company/info?symbol=TCS     # Get company information
- /api/company/history             # Get historical price data
- /api/company/financials          # Get financial metrics
- /news/analyze-full?symbol=TCS   # Get news with sentiment analysis
```

### CSS Architecture

#### main.css
- CSS variables for theming (colors, shadows, spacing)
- Global reset and base styles
- Typography system
- Button & badge components
- Utility classes (spacing, text, flexbox, grid)

#### navbar.css
- Header styling with sticky positioning
- Search bar with focus effects
- Navigation tabs with active states
- Breadcrumb navigation
- Company header display

#### cards.css
- Reusable card components
- Data grid/table styling
- Metric cards for KPIs
- Stats rows for key information
- Tab content animations
- Empty state messaging

#### loading.css
- Progress bar with smooth animations
- Toast notification system
- Loading spinners
- Skeleton loading placeholders
- Full-screen loading overlay

### JavaScript Architecture

#### loader.js
- **Loader.start()** - Begin loading bar animation
- **Loader.finish()** - Complete loading bar
- **Loader.showError()** - Show error toast
- **Loader.showSuccess()** - Show success toast
- **Loader.showOverlay()** - Show full-screen loader
- Toast notification system with auto-cleanup

#### ui.js
- **formatCurrency()** - Format rupee values
- **formatLargeNumber()** - Format numbers with K, Cr notation
- **formatPercent()** - Format percentage values
- **switchTab()** - Switch between navigation tabs
- **createMetricCard()** - Generate metric card HTML
- **debounce()** & **throttle()** - Performance optimization helpers
- HTML/DOM helper functions

#### api.js
- **API.get()** - Make GET requests with loading bar
- **API.post()** - Make POST requests
- Timeout handling & request cancellation
- Pre-built methods:
  - `getNifty50()` - Get Nifty companies
  - `getCompanyInfo(symbol)` - Get company info
  - `getStockHistory(symbol, start, end)` - Get price history
  - `getFinancials(symbol)` - Get financial data
  - `getNewsAnalysis(symbol)` - Get news with sentiment

#### app.js
- **App.init()** - Initialize the application
- **App.loadCompanyData(symbol)** - Main data fetching orchestrator
- Tab-specific loaders:
  - `loadOverviewTab()` - Render company overview
  - `loadChartTab()` - Render price chart
  - `loadAnalysisTab()` - Render financial analysis
  - `loadFinancialsTab()` - Render financial statements
  - `loadNewsTab()` - Render news with sentiment
- URL parameter handling for direct stock links

## 🚀 How to Use

### Starting the Application

1. **Start Backend Server:**
```bash
cd backend
python app.py
# Server runs on http://localhost:5000
```

2. **Start Frontend Server:**
```bash
cd frontend
python server.py
# Application runs on http://localhost:8000
```

3. **Open in Browser:**
```
http://localhost:8000
```

### Searching for a Stock

1. Use the search bar at the top to search for a stock symbol (e.g., TCS, RELIANCE)
2. Press Enter or click search
3. The loading bar will appear while data is fetched
4. Company overview and metrics will load automatically
5. Click tabs to view different analysis sections
6. Wait for toast notifications if any data is slow to fetch

## 📊 Data Flow

```
User Input (Search)
    ↓
App.init() → handleSearchSubmit()
    ↓
App.loadCompanyData(symbol)
    ↓
API calls (loader.js shows progress bar)
    ↓
Data → UI Rendering (ui.js formatting)
    ↓
Content displays with animations
```

## 🎯 Key Features Implemented

✅ Modern Screener.in-like UI design
✅ Animated loading bar for all API requests
✅ Toast notifications for success/error messages
✅ Navigation tabs for different analysis sections
✅ Responsive grid layouts (mobile, tablet, desktop)
✅ Currency & number formatting (INR, Cr, L, K)
✅ Sentiment analysis integration with FinBERT
✅ Error handling with user-friendly messages
✅ Performance optimization (debounce, throttle)
✅ Modular JavaScript for easy debugging
✅ Organized CSS with CSS variables for theming

## 🐛 Debugging Guide

### 1. **Check Loading Bar**
- Located in `css/loading.css`
- All API calls automatically show loading bar from `js/loader.js`
- Customize timing in `loader.js` (REQUEST_TIMEOUT = 30000ms)

### 2. **Tab Navigation Issues**
- Check `js/app.js` → `setupEventListeners()`
- Tab content managed in `JS/ui.js` → `switchTab()`
- CSS transitions in `css/cards.css` → `.tab-content.active`

### 3. **API Response Issues**
- Check network tab in DevTools
- Verify backend is running on port 5000
- Check CORS headers in backend

### 4. **Styling Issues**
- CSS variables defined in `css/main.css` (--primary-bg, --info, etc.)
- Modify colors globally in `:root {}` selector
- Component-specific styles in respective CSS files

### 5. **Data Display Issues**
- Check `js/ui.js` formatting functions
- Verify API response structure in `js/api.js`
- Check tab rendering in `js/app.js` (renderXxxTab functions)

## 📱 Responsive Breakpoints

- **Desktop**: 1024px+
- **Tablet**: 768px - 1023px
- **Mobile**: < 768px
- **Small Mobile**: < 480px

Media queries in:
- `css/main.css` - Base responsive styles
- `css/navbar.css` - Header responsiveness
- `index.html` - Custom responsive styles

## 🔒 Security Considerations

- API requests use CORS
- Sensitive data should be handled in backend
- Input validation on search queries
- Error messages don't expose sensitive information

## 📝 Future Enhancements

- Add Chart.js for price charts
- Add peer comparison table
- Add financial statement comparisons
- Add technical analysis indicators
- Add watchlist functionality
- Add price alerts
- Add export to PDF/Excel
- Add dark/light theme toggle
