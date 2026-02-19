# Stockit UI - Quick Start Guide

## 🚀 Getting Started

### Prerequisites
- Python 3.x installed
- Backend running (Flask app)
- Modern web browser

### Setup & Run

#### 1️⃣ Start Backend
```bash
cd backend
pip install -r requirements.txt
python app.py
```
Backend will run on `http://localhost:5000`

#### 2️⃣ Start Frontend
```bash
cd frontend
python server.py
```
Frontend will run on `http://localhost:8000`

#### 3️⃣ Open in Browser
```
http://localhost:8000
```

## 💡 Using the Application

### Search for Stock
1. Enter a stock symbol (e.g., TCS, RELIANCE, INFY) in the search bar
2. Press Enter or wait for autocomplete
3. Loading bar appears at the top
4. Stock data loads automatically

### Navigation Tabs
- **📊 Overview** - Company basics and key metrics
- **📈 Chart** - Price movement visualization
- **💹 Analysis** - Financial metrics analysis
- **💰 Financials** - Balance sheet, P&L, cash flow
- **👥 Peers** - Compare with peer companies
- **📰 News & Sentiment** - Read news with AI sentiment analysis
- **📄 Documents** - Official documents & announcements

### Features

#### 🔄 Loading States
- **Progress Bar** - Shows progress of data loading
- **Toast Notifications** - Feedback messages (success/error/warning)
- **Skeleton Loading** - Placeholder while data loads
- **Loading Overlay** - Full-screen loader for long operations

#### 📊 Data Display
- **Key Metrics** - P/E, Market Cap, 52W High/Low
- **Company Summary** - Business description
- **Financial Tables** - Structured financial data
- **Price Charts** - Historical price visualization
- **News Items** - Latest news with sentiment scores

## 📁 Project Structure

```
/frontend
  ├── index.html              ← Main app (loads CSS & JS modules)
  ├── server.py              ← Flask development server
  ├── ARCHITECTURE.md        ← Full technical documentation
  │
  ├── css/                   ← Styles (modular by component)
  │   ├── main.css          ← Global styles & variables
  │   ├── navbar.css        ← Header & navigation
  │   ├── cards.css         ← Card components & tables
  │   └── loading.css       ← Loading bars & toasts
  │
  └── js/                    ← JavaScript (modular by function)
      ├── loader.js         ← Loading indicators
      ├── ui.js             ← UI utilities & formatting
      ├── api.js            ← API calls & data fetching
      └── app.js            ← Main application logic
```

## 🎯 Customization

### Change Colors
Edit `css/main.css` - modify `:root` CSS variables:
```css
:root {
    --primary-bg: #0d1117;
    --info: #58a6ff;
    /* ... other colors ... */
}
```

### Change API Endpoint
Edit `js/api.js` - modify `BASE_URL`:
```javascript
const BASE_URL = 'http://localhost:5000/api'; // Change this
```

### Add Loading Delay
Edit `js/loader.js` - modify `REQUEST_TIMEOUT`:
```javascript
const REQUEST_TIMEOUT = 30000; // Milliseconds
```

## 🆘 Troubleshooting

### "Cannot GET /"
- Make sure frontend server is running: `python server.py`
- Check if running on correct port (8000)

### "API request failed"
- Ensure backend is running on port 5000
- Check browser console for CORS errors
- Verify stock symbol is correct

### Loading bar not showing
- Check `browser console` for JavaScript errors
- Verify `js/loader.js` is loaded in Network tab
- Check if API call takes < 100ms (too fast to see)

### Tab content not loading
- Check browser DevTools → Network tab for API failures
- Look for error toasts in bottom-right
- Check if backend endpoints are responding

## 📊 API Integration

### Supported Endpoints
```
GET /api/nifty50
    → List of Nifty 50 companies

GET /api/company/info?symbol=TCS
    → Company basic info (name, price, summary)

GET /api/company/history?symbol=TCS&start=2024-01-01&end=2024-12-31
    → Historical OCHLV data

GET /api/company/financials?symbol=TCS
    → Financial metrics (revenue, profit, etc.)

GET /api/news/analyze-full?symbol=TCS
    → News headlines with sentiment analysis
```

## 🎨 UI Theme

The UI uses a **dark theme** inspired by GitHub's design:
- Dark background (#0d1117)
- Light text (#e6edf3)
- Blue accents (#58a6ff)
- Green for positive/up (#3fb950)
- Red for negative/down (#f85149)
- Yellow for neutral/warning (#d29922)

To switch to light theme, modify CSS variables in `css/main.css`.

## 📱 Responsive Design

Works on all devices:
- ✅ Desktop (1024px+)
- ✅ Tablet (768px - 1023px)
- ✅ Mobile (< 768px)
- ✅ Small phones (< 480px)

## 🔧 Development

### Add New Tab
1. Add button in `index.html`:
```html
<button class="nav-tab" data-tab="mytab">📌 My Tab</button>
```

2. Add content div:
```html
<div id="tab-mytab" class="tab-content"></div>
```

3. Add loader in `js/app.js`:
```javascript
const loadMyTab = async () => {
    const tabContent = document.getElementById('tab-mytab');
    // Fetch data and render
}
```

### Add New CSS Component
1. Create in appropriate file (`css/cards.css`, `css/navbar.css`, etc.)
2. Use existing CSS variables for colors
3. Follow naming convention (`.component-name`)
4. Test on mobile viewports

### Debug Mode
Open browser DevTools (F12):
- **Console** - Check for JavaScript errors
- **Network** - Monitor API calls
- **Elements** - Inspect HTML/CSS
- **Performance** - Check page load time

## 📞 Support & Documentation

For detailed technical information, see `ARCHITECTURE.md`:
- Complete Module Reference
- Data Flow Diagram
- Debugging Guide
- Advanced Customization

## 📈 Performance Tips

1. **Reduce API calls** - Cache data client-side
2. **Lazy load tabs** - Load data only when tab clicked
3. **Compress images** - Optimize any media assets
4. **Minify CSS/JS** - In production build
5. **Use CDN** - For external libraries

## 📄 License

This project is part of the Stockit Consultancy Project.
