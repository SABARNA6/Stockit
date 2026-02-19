#!/usr/bin/env python3
"""
Simple HTTP server to serve the frontend.
Run this in the frontend directory to serve the HTML files.
"""

import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 8000
HANDLER = http.server.SimpleHTTPRequestHandler

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add headers to prevent caching
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"Frontend Server Running!")
        print(f"{'='*60}")
        print(f"Frontend: http://localhost:{PORT}")
        print(f"Backend:  http://localhost:5000/api")
        print(f"\nMake sure the Flask backend is running on port 5000!")
        print(f"{'='*60}\n")
        
        try:
            # Try to open browser
            webbrowser.open(f'http://localhost:{PORT}')
        except:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
