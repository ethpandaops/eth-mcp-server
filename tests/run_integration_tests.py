#!/usr/bin/env python3
"""
Runner script for integration tests.

This script ensures the MCP server is running before executing tests.
"""

import subprocess
import time
import sys
import os
import signal
import requests
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def is_server_running(url="http://localhost:8000/mcp"):
    """Check if the MCP server is running."""
    try:
        response = requests.post(url, json={"method": "eth_listWallets", "params": {}}, timeout=1)
        return response.status_code == 200
    except:
        return False


def start_server():
    """Start the MCP server in a subprocess."""
    print("Starting MCP server...")
    
    # Start server in background
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid if sys.platform != "win32" else None
    )
    
    # Wait for server to start
    max_attempts = 30
    for i in range(max_attempts):
        if is_server_running():
            print("✓ MCP server is running")
            return server_process
        time.sleep(1)
        print(f"Waiting for server to start... ({i+1}/{max_attempts})")
    
    # If server didn't start, kill process and exit
    if sys.platform != "win32":
        os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
    else:
        server_process.terminate()
    
    print("❌ Failed to start MCP server")
    sys.exit(1)


def run_tests():
    """Run the integration tests."""
    print("\nRunning integration tests...")
    
    # Run pytest with coverage
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest", 
            "tests/test_integration.py",
            "-v",
            "--tb=short",
            "--color=yes"
        ],
        cwd=Path(__file__).parent.parent
    )
    
    return result.returncode == 0


def main():
    """Main function."""
    server_process = None
    
    try:
        # Check if server is already running
        if is_server_running():
            print("✓ MCP server is already running")
        else:
            # Start server
            server_process = start_server()
            time.sleep(2)  # Give server time to fully initialize
        
        # Run tests
        success = run_tests()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
        
    finally:
        # Clean up server process if we started it
        if server_process:
            print("\nStopping MCP server...")
            if sys.platform != "win32":
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
            else:
                server_process.terminate()
            server_process.wait()
            print("✓ MCP server stopped")


if __name__ == "__main__":
    main()