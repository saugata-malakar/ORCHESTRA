import sys
import os
from pathlib import Path

# Add the code directory to the Python path
code_dir = Path(__file__).parent.parent / "code"
sys.path.append(str(code_dir))

# Import the Flask app
from app import app

# Ensure the agent initializes before the first request
with app.app_context():
    try:
        from app import init_agent
        init_agent()
    except Exception as e:
        print("Initialization error on Vercel:", e)
