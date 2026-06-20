#!/usr/bin/env python3
"""
Kronos Web UI startup script (FastAPI version) - Unicode Safe
"""

import os
import sys
import subprocess
import webbrowser
import time

def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import jinja2
        import pandas
        import numpy
        import plotly
        print("[OK] All dependencies installed")
        return True
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Please run: pip install fastapi uvicorn jinja2 pandas numpy plotly")
        return False

def install_dependencies():
    """Install dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "jinja2", "pandas", "numpy", "plotly"])
        print("[OK] Dependencies installation completed")
        return True
    except subprocess.CalledProcessError:
        print("[ERROR] Dependencies installation failed")
        return False

def main():
    """Main function"""
    print("[START] Starting Kronos Web UI (FastAPI)...")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("\nAuto-install dependencies? (y/n): ", end="")
        if input().lower() == 'y':
            if not install_dependencies():
                return
        else:
            print("Please manually install dependencies and retry")
            return
    
    # Check model availability
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from model import Kronos, KronosTokenizer, KronosPredictor
        print("[OK] Kronos model library available")
    except ImportError:
        print("[WARNING] Kronos model library not available, will use simulated prediction")
    
    # Start FastAPI application via Uvicorn
    print("\n[SERVER] Starting Uvicorn web server...")
    
    # Start server
    try:
        import uvicorn
        print("[OK] Web server started successfully!")
        print(f"[SERVER] Access URL: http://localhost:7070")
        print("[TIP] Tip: Press Ctrl+C to stop server")
        
        # Auto-open browser
        time.sleep(2)
        webbrowser.open('http://localhost:7070')
        
        # Run uvicorn server programmatically
        # Note: we pass string "app:app" to support hot reloading in development.
        # We also need to set app directory to current directory so uvicorn can find the app module.
        app_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, app_dir)
        os.chdir(app_dir)
        uvicorn.run("app:app", host="0.0.0.0", port=7070, reload=True)
        
    except Exception as e:
        print(f"[ERROR] Startup failed: {e}")
        print("Please check if port 7070 is occupied")

if __name__ == "__main__":
    main()
