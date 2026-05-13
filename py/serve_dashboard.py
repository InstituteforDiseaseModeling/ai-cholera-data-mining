#!/usr/bin/env python3
"""
Simple HTTP server for the MOSAIC AI Cholera Dashboard
This resolves CORS issues when loading CSV files from the data tabs.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

def serve_dashboard(port=8002):
    """Start a local HTTP server and open the dashboard."""
    
    # Change to the project root directory (parent of py/)
    os.chdir(Path(__file__).parent.parent)
    
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory='.', **kwargs)
    
    try:
        with socketserver.TCPServer(('', port), Handler) as httpd:
            dashboard_url = f'http://localhost:{port}/dashboard/dashboard.html'
            print(f"🚀 Starting MOSAIC AI Cholera Dashboard server...")
            print(f"📊 Dashboard URL: {dashboard_url}")
            print(f"📁 Serving files from: {Path.cwd()}")
            print(f"🌐 Server running on port {port}")
            print(f"\n✨ Opening dashboard in your browser...")
            
            # Open dashboard in browser
            webbrowser.open(dashboard_url)
            
            print(f"\n🔧 The data tabs should now work properly!")
            print(f"🔍 Check the browser console for debugging info if needed.")
            print(f"\n⏹️  Press Ctrl+C to stop the server")
            
            # Keep server running
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print(f"\n🛑 Server stopped")
                httpd.shutdown()
                
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is already in use. Try a different port:")
            print(f"   python3 serve_dashboard.py --port 8003")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Serve the MOSAIC AI Cholera Dashboard")
    parser.add_argument("--port", type=int, default=8002, help="Port to serve on (default: 8002)")
    
    args = parser.parse_args()
    serve_dashboard(args.port)