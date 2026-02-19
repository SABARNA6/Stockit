# Stockit Frontend Structure & Debugging Reference

## 📊 File Structure Tree

```
frontend/
├── 📄 index.html                    # Entry point - loads CSS & JS
├── 🐍 server.py                     # Development server
├── 📋 README.md                     # Quick start guide
├── 📖 ARCHITECTURE.md               # Full technical documentation
│
├── 📁 css/
│   ├── 🎨 main.css                 # Global styles & CSS variables
│   ├── 🎨 navbar.css               # Header, search bar, tabs
│   ├── 🎨 cards.css                # Card components, tables, grids
│   └── 🎨 loading.css              # Progress bars, spinners, toasts
│
├── 📁 js/
│   ├── ⚙️  loader.js               # Loading indicators & notifications
│   ├── ⚙️  ui.js                   # UI utilities & formatting
│   ├── ⚙️  api.js                  # API calls & data fetching
│   └── ⚙️  app.js                  # Main app logic & controllers
│
└── 📁 components/                  # For future component-based architecture
```

## 🔗 Module Dependencies

```
index.html
    ├── links: css/main.css
    ├── links: css/navbar.css
    ├── links: css/cards.css
    ├── links: css/loading.css
    │
    ├── script: js/loader.js         (no dependencies)
    ├── script: js/ui.js             (depends on Loader)
    ├── script: js/api.js            (depends on Loader)
    └── script: js/app.js            (depends on Loader, UI, API)
```

## 🎯 What Each File Does

### HTML (index.html)
```
Header
├── Logo & Search Bar
├── Navigation Tabs (Overview, Chart, Analysis, etc.)
└── Company Header (displays when stock loaded)

Main Content
├── Tab: Overview
├── Tab: Chart
├── Tab: Analysis
├── Tab: Financials
├── Tab: Peers
├── Tab: News & Sentiment
└── Tab: Documents

Footer
└── Copyright & Credits
```

### CSS Files

#### css/main.css
- **Imports:** None
- **Exports:** CSS variables, global styles
- **Contains:**
  - Color scheme (primary, secondary, status colors)
  - Typography (h1-h6, p, a)
  - Global utilities (spacing, flexbox, grid)
  - Button & badge styles

#### css/navbar.css
- **Imports:** Uses variables from main.css
- **Exports:** Navbar styles
- **Contains:**
  - Header styling
  - Logo design
  - Search bar styles
  - Navigation tabs (active/hover states)
  - Breadcrumb & company header

#### css/cards.css
- **Imports:** Uses variables from main.css
- **Exports:** Card component styles
- **Contains:**
  - Card containers & headers
  - Data grid/table styles
  - Metric cards
  - Stats rows
  - Tab content animations

#### css/loading.css
- **Imports:** Uses variables from main.css
- **Exports:** Loading animation styles
- **Contains:**
  - Progress bar animations
  - Toast notification styles
  - Loading spinner
  - Skeleton placeholders
  - Loading overlay

### JavaScript Files

#### js/loader.js (⚙️ CORE)
**Purpose:** Handle all loading states & notifications
**Main Functions:**
- `Loader.start()` - Start progress bar
- `Loader.finish()` - End progress bar
- `Loader.showError(msg)` - Show error toast
- `Loader.showSuccess(msg)` - Show success toast
- `Loader.showOverlay(msg)` - Show full-screen loader
- `Loader.hideOverlay()` - Hide full-screen loader

**Dependencies:** None
**Used By:** api.js, app.js

#### js/ui.js (🎨 UTILITIES)
**Purpose:** Provide UI helper functions
**Main Functions:**
- `UI.formatCurrency(value)` - Format as ₹
- `UI.formatLargeNumber(value)` - Format as K, L, Cr
- `UI.formatPercent(value)` - Format as %
- `UI.switchTab(name)` - Switch active tab
- `UI.createMetricCard()` - Generate HTML
- `UI.debounce(func, wait)` - Optimize function calls
- `UI.throttle(func, limit)` - Limit function calls

**Dependencies:** Loader
**Used By:** app.js

#### js/api.js (🔌 API)
**Purpose:** Handle all backend API calls
**Main Functions:**
- `API.get(endpoint, params)` - GET request
- `API.post(endpoint, data)` - POST request
- `API.getNifty50()` - Get Nifty companies
- `API.getCompanyInfo(symbol)` - Get stock info
- `API.getStockHistory()` - Get price history
- `API.getFinancials(symbol)` - Get financial data
- `API.getNewsAnalysis(symbol)` - Get news & sentiment

**Dependencies:** Loader
**Used By:** app.js
**Backend:** Connects to http://localhost:5000/api

#### js/app.js (🚀 MAIN APP)
**Purpose:** Main application logic & orchestration
**Main Functions:**
- `App.init()` - Initialize app
- `App.loadCompanyData(symbol)` - Main data loader
- `App.loadAllTabs()` - Load all tab data
- `renderCompanyHeader()` - Display company info
- `loadOverviewTab()` - Load overview data
- `loadChartTab()` - Load chart data
- `loadAnalysisTab()` - Load analysis data
- `loadFinancialsTab()` - Load financials
- `loadNewsTab()` - Load news & sentiment

**Dependencies:** Loader, UI, API
**Used By:** index.html

## 🔄 Data Flow Example

### When User Searches for a Stock

```
User types "TCS" in search bar
    ↓
handleSearchSubmit() [in app.js]
    ↓
App.loadCompanyData("TCS")
    ↓
API.getCompanyInfo("TCS") {
    Loader.start() → [loader.js shows progress bar]
        ↓
    fetch() to /api/company/info?symbol=TCS
        ↓
    Loader.finish() → [progress bar completes]
        ↓
    return data
}
    ↓
renderCompanyHeader(data) {
    UI.formatCurrency(data.price) → ₹356.50
    Update DOM with company info
}
    ↓
loadAllTabs() {
    loadChartTab()
    loadAnalysisTab()
    loadFinancialsTab()
    loadNewsTab()
}
    ↓
UI displayed with animations
```

## 🐛 Common Issues & Solutions

### Issue: Loading bar doesn't show
**File:** css/loading.css
**Fix:** Check `.loading-bar { animation: loadingBar ... }`

### Issue: API request fails silently
**File:** js/api.js
**Debug:** Add console.log() in try-catch blocks
**Check:** Browser DevTools → Console tab

### Issue: Tab content not switching
**File:** js/ui.js (switchTab function)
**Debug:** Check if `.active` class is being applied
**Check:** DevTools → Elements tab for .nav-tab.active

### Issue: Styling looks wrong
**File:** css/main.css (CSS variables)
**Fix:** Check if colors are defined in :root
**Debug:** Right-click element → Inspect to see applied styles

### Issue: Performance slow
**Files:** js/app.js (too many API calls)
**Fix:** Add debounce to search input in handleSearch()
**Check:** DevTools → Network tab for waterfall of requests

## 📊 CSS Variable Reference

```css
/* Colors */
--primary-bg: #0d1117          /* Main background */
--secondary-bg: #161b22        /* Card background */
--tertiary-bg: #21262d         /* Input background */

/* Text */
--text-primary: #e6edf3        /* Main text */
--text-secondary: #8b949e      /* Secondary text */
--text-muted: #6e7681          /* Muted text */

/* Status */
--success: #3fb950             /* Green - positive */
--danger: #f85149              /* Red - negative */
--warning: #d29922             /* Yellow - warning */
--info: #58a6ff                /* Blue - info */

/* Borders */
--border-color: #30363d        /* Main border */
--shadow-sm: 0 3px 12px ...   /* Small shadow */
```

## 🚀 Quick Command Reference

```bash
# Start backend
cd backend && python app.py

# Start frontend
cd frontend && python server.py

# View application
http://localhost:8000

# Debug: Check console
F12 → Console tab

# Debug: Network requests
F12 → Network tab
```

## 📈 Performance Checklist

- [ ] Loading bar shows within 100ms of API call
- [ ] Toast notifications appear in < 500ms
- [ ] Tab switching is instant
- [ ] Page loads in < 2 seconds
- [ ] No console errors
- [ ] No CORS warnings
- [ ] Images optimized (if added)
- [ ] CSS is minified (in production)

## 🔄 Update Flow for New Features

1. **Add HTML**: index.html (new tab/section)
2. **Add CSS**: css/*.css (new component styles)
3. **Add JS**: js/app.js (new tab loader function)
4. **Test**: Browser DevTools
5. **Document**: Update ARCHITECTURE.md

