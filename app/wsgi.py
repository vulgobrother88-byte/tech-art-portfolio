import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_PATH = os.getenv("PROJECT_PATH", "/home/techappuai/techart")
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

load_dotenv(Path(PROJECT_PATH) / ".env", override=True)
from app import create_app
application = create_app()
