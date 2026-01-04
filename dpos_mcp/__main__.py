import sys
from pathlib import Path

# Force project root on sys.path (Claude does not guarantee cwd)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dpos_mcp.server import run_stdio_server

run_stdio_server()
