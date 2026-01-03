#!/usr/bin/env python3
"""
DPOS Backend Startup Script
Starts the FastAPI backend server with all required services.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_neo4j():
    """Check if Neo4j is accessible."""
    try:
        from src.graph.manager import Neo4jManager
        with Neo4jManager() as manager:
            result = manager.run_query("RETURN 1 as test")
            print("[OK] Neo4j connection successful")
            return True
    except Exception as e:
        print(f"[WARN] Neo4j not accessible: {e}")
        print("       Some features may be limited without Neo4j")
        return False


def check_ollama():
    """Check if Ollama is running for embeddings."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("[OK] Ollama is running")
            return True
    except Exception:
        pass
    print("[WARN] Ollama not accessible - using fallback embeddings")
    return False


def main():
    print("=" * 50)
    print("DPOS - Data Product Operating System")
    print("Starting Backend Server...")
    print("=" * 50)

    # Check dependencies
    print("\nChecking dependencies...")
    check_neo4j()
    check_ollama()

    # Start the FastAPI server
    print("\n" + "=" * 50)
    print("Starting FastAPI server on http://localhost:8000")
    print("API docs available at http://localhost:8000/docs")
    print("=" * 50 + "\n")

    os.chdir(project_root)

    try:
        # Use uvicorn to run the FastAPI app
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "src.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
