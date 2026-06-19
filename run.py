import uvicorn
import os
import sys

# Project root is the directory of this file
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("BACKEND_PORT", "5000")),
        reload=False,
    )
