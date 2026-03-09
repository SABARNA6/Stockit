# Stockit Frontend

This is a modern, data-centric frontend for the Stockit platform, inspired by Screener.in's clean and professional aesthetic.

## Features
- **Real-time Search**: Search for any Nifty 50 company with instant suggestions.
- **Stock Dashboard**: Clear view of company price, symbol, and key metrics.
- **Interactive Price Charts**: Historical price action powered by Chart.js.
- **Financial Highlights**: Quick look at Revenue, Net Profit, and EBITDA margins.
- **Sentiment Analysis**: News headlines analyzed by FinBERT to give you an "Overall Sentiment" snapshot.
- **Modern UI**: Built with a focus on typography, whitespace, and readability.

## Folder Structure
- `index.html`: Main entry point.
- `css/style.css`: Premium styling with Inter font and responsive layout.
- `js/api.js`: Modular API client for backend communication.
- `js/app.js`: Application logic and UI orchestration.

## How to Run

1. **Start the Backend**:
   - Ensure you are in the `backend` directory.
   - Install dependencies: `pip install -r requirements.txt`.
   - Run the server: `python app.py`.
   - The backend will run on `http://127.0.0.1:5000`.

2. **Run the Frontend**:
   - Serve the `client` folder using a local web server.
   - Example using Python: `python -m http.server 8000` inside the `client` folder.
   - Open `http://localhost:8000` in your browser.

*Note: Opening `index.html` directly as a file might block ES modules and API requests due to CORS and browser security policies. Please use a local server.*
