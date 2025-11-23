#!/usr/bin/env python3
"""
Email Productivity Agent - Backend Server
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def main():
    """Main entry point for the backend server"""
    
    # Check for required environment variables
    required_vars = []
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("Warning: The following environment variables are not set:")
        for var in missing_vars:
            print(f"  - {var}")
        print("The application will run in mock mode.\n")
    
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info")
    
    print("=" * 60)
    print("Email Productivity Agent - Backend Server")
    print("=" * 60)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Reload: {reload}")
    print(f"Log Level: {log_level}")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()