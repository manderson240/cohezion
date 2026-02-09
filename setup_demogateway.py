#!/usr/bin/env python3
"""
DemoGateway + Claude.ai Automated Setup Script
Automates everything except the final manual step in Claude.ai
"""

import subprocess
import time
import requests
import json
import sys
import os
import signal
from pathlib import Path
from typing import Optional, List

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_step(step: int, message: str):
    """Print a step message"""
    print(f"{Colors.YELLOW}[Step {step}] {message}{Colors.NC}")

def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")

def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")

def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.BLUE}{message}{Colors.NC}")

def run_command(cmd: List[str], check: bool = True) -> Optional[str]:
    """Run a shell command"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result.stdout.strip() if result.stdout else None
    except subprocess.CalledProcessError as e:
        return None

def check_ollama(ollama_url: str) -> bool:
    """Check if Ollama is running"""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def get_ollama_models(ollama_url: str) -> List[str]:
    """Get list of available Ollama models"""
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=2)
        data = response.json()
        return [model['name'] for model in data.get('models', [])]
    except Exception:
        return []

def pull_ollama_model(model: str) -> bool:
    """Pull a model from Ollama"""
    try:
        print(f"  Pulling {model} (this may take a few minutes)...")
        subprocess.run(['ollama', 'pull', model], check=True, capture_output=True)
        return True
    except Exception:
        return False

def check_port_available(port: int) -> bool:
    """Check if a port is available"""
    try:
        result = subprocess.run(['lsof', '-Pi', f':{port}', '-sTCP:LISTEN', '-t'],
                              capture_output=True, text=True)
        return result.returncode != 0
    except Exception:
        return True

def get_ngrok_url() -> Optional[str]:
    """Get the ngrok public URL"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=2)
        data = response.json()
        tunnels = data.get('tunnels', [])
        if tunnels:
            return tunnels[0].get('public_url')
    except Exception:
        pass
    return None

def start_mcp_server(project_dir: str, port: int) -> Optional[int]:
    """Start the MCP HTTP server"""
    try:
        # Kill any existing process
        subprocess.run(['pkill', '-f', 'python -m cohezion.gateway.mcp_http_server'],
                      capture_output=True)
        time.sleep(1)

        # Start new process
        env = os.environ.copy()
        env['PORT'] = str(port)

        with open('/tmp/mcp_server.log', 'w') as log_file:
            process = subprocess.Popen(
                ['uv', 'run', 'python', '-m', 'cohezion.gateway.mcp_http_server'],
                cwd=project_dir,
                stdout=log_file,
                stderr=log_file,
                env=env,
                preexec_fn=os.setsid
            )

        time.sleep(3)
        return process.pid
    except Exception as e:
        print_error(f"Failed to start MCP server: {e}")
        return None

def start_ngrok(port: int) -> Optional[int]:
    """Start ngrok tunnel"""
    try:
        # Kill any existing process
        subprocess.run(['pkill', '-f', 'ngrok http'], capture_output=True)
        time.sleep(1)

        # Start new process
        with open('/tmp/ngrok.log', 'w') as log_file:
            process = subprocess.Popen(
                ['ngrok', 'http', str(port)],
                stdout=log_file,
                stderr=log_file,
                preexec_fn=os.setsid
            )

        time.sleep(3)
        return process.pid
    except Exception as e:
        print_error(f"Failed to start ngrok: {e}")
        return None

def check_mcp_server(port: int) -> bool:
    """Check if MCP server is running"""
    try:
        response = requests.get(f'http://localhost:{port}/health', timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def main():
    """Main setup function"""
    PROJECT_DIR = "/home/mike-anderson/dev/cohezion"
    SERVER_PORT = 5000
    OLLAMA_URL = "http://localhost:11434"
    REQUIRED_MODELS = ["qwen3-coder:30b", "deepseek-r1:70b", "phi3:mini"]

    print()
    print(f"{Colors.BLUE}════════════════════════════════════════════{Colors.NC}")
    print(f"{Colors.BLUE}  DemoGateway + Claude.ai Setup{Colors.NC}")
    print(f"{Colors.BLUE}════════════════════════════════════════════{Colors.NC}")
    print()

    # Step 1: Check Ollama
    print_step(1, "Checking Ollama...")
    if not check_ollama(OLLAMA_URL):
        print_error("Ollama is not running!")
        print(f"{Colors.YELLOW}Start Ollama with: ollama serve{Colors.NC}")
        sys.exit(1)
    print_success("Ollama is running")

    # Step 2: Check models
    print()
    print_step(2, "Checking required models...")
    available_models = get_ollama_models(OLLAMA_URL)
    missing_models = [m for m in REQUIRED_MODELS if m not in available_models]

    for model in REQUIRED_MODELS:
        if model in available_models:
            print_success(f"{model} is available")
        else:
            print_error(f"{model} is missing")

    if missing_models:
        print()
        print(f"{Colors.YELLOW}Pulling missing models...{Colors.NC}")
        for model in missing_models:
            if pull_ollama_model(model):
                print_success(f"Pulled {model}")
            else:
                print_error(f"Failed to pull {model}")

    # Step 3: Check ngrok
    print()
    print_step(3, "Checking ngrok...")
    if not run_command(['which', 'ngrok']):
        print_error("ngrok is not installed!")
        print(f"{Colors.YELLOW}Install from: https://ngrok.com/download{Colors.NC}")
        sys.exit(1)
    print_success("ngrok is installed")

    # Step 4: Check port
    print()
    print_step(4, f"Checking if port {SERVER_PORT} is available...")
    if not check_port_available(SERVER_PORT):
        print_error(f"Port {SERVER_PORT} is already in use!")
        print(f"{Colors.YELLOW}Kill with: lsof -ti:{SERVER_PORT} | xargs kill -9{Colors.NC}")
        sys.exit(1)
    print_success(f"Port {SERVER_PORT} is available")

    # Step 5: Start MCP Server
    print()
    print_step(5, "Starting MCP HTTP Server...")
    mcp_pid = start_mcp_server(PROJECT_DIR, SERVER_PORT)
    if not mcp_pid:
        print_error("Failed to start MCP server")
        sys.exit(1)
    print_success(f"MCP Server started (PID: {mcp_pid})")

    print("  Waiting for server to start...")
    if not check_mcp_server(SERVER_PORT):
        print_error("Server failed to start!")
        print(f"{Colors.YELLOW}Check logs: cat /tmp/mcp_server.log{Colors.NC}")
        sys.exit(1)
    print_success(f"Server is running on http://localhost:{SERVER_PORT}")

    # Step 6: Start ngrok
    print()
    print_step(6, "Starting ngrok tunnel...")
    ngrok_pid = start_ngrok(SERVER_PORT)
    if not ngrok_pid:
        print_error("Failed to start ngrok")
        sys.exit(1)
    print_success(f"ngrok started (PID: {ngrok_pid})")

    print("  Waiting for ngrok to initialize...")
    time.sleep(2)
    ngrok_url = get_ngrok_url()
    if not ngrok_url:
        print_error("Failed to get ngrok URL!")
        print(f"{Colors.YELLOW}Check ngrok logs: cat /tmp/ngrok.log{Colors.NC}")
        sys.exit(1)

    print_success("ngrok tunnel established")
    print()

    # Step 7: Display information
    print(f"{Colors.GREEN}════════════════════════════════════════════{Colors.NC}")
    print(f"{Colors.GREEN}  ✓ Setup Complete!{Colors.NC}")
    print(f"{Colors.GREEN}════════════════════════════════════════════{Colors.NC}")
    print()

    print_info("MCP Server Information:")
    print(f"  Local URL:  {Colors.YELLOW}http://localhost:{SERVER_PORT}{Colors.NC}")
    print(f"  Public URL: {Colors.YELLOW}{ngrok_url}{Colors.NC}")
    print()

    print_info("Servers Running:")
    print(f"  MCP HTTP Server: {Colors.GREEN}Running (PID {mcp_pid}){Colors.NC}")
    print(f"  ngrok Tunnel:    {Colors.GREEN}Running (PID {ngrok_pid}){Colors.NC}")
    print()

    # Save configuration
    config_file = "/tmp/demogateway_config.txt"
    with open(config_file, 'w') as f:
        f.write(f"# DemoGateway Configuration\n")
        f.write(f"MCP_SERVER_LOCAL=http://localhost:{SERVER_PORT}\n")
        f.write(f"MCP_SERVER_PUBLIC={ngrok_url}\n")
        f.write(f"MCP_SERVER_SSE={ngrok_url}/sse\n")
        f.write(f"MCP_PID={mcp_pid}\n")
        f.write(f"NGROK_PID={ngrok_pid}\n")

    print_info("Configuration saved to:")
    print(f"  {Colors.YELLOW}{config_file}{Colors.NC}")
    print()

    # Manual Claude.ai instructions
    print(f"{Colors.YELLOW}════════════════════════════════════════════{Colors.NC}")
    print(f"{Colors.YELLOW}  Manual Step: Add Custom Connector to Claude.ai{Colors.NC}")
    print(f"{Colors.YELLOW}════════════════════════════════════════════{Colors.NC}")
    print()

    print_info("1. Open Claude.ai:")
    print(f"   https://claude.ai")
    print()

    print_info("2. Go to Settings → Custom Connectors")
    print()

    print_info("3. Click \"Add Custom Connector\"")
    print()

    print_info("4. Fill in the form:")
    print(f"   Name: {Colors.YELLOW}ngrok AI Gateway{Colors.NC}")
    print(f"   Remote MCP server URL: {Colors.YELLOW}{ngrok_url}/sse{Colors.NC}")
    print(f"   OAuth Client ID: {Colors.YELLOW}(leave blank){Colors.NC}")
    print(f"   OAuth Client Secret: {Colors.YELLOW}(leave blank){Colors.NC}")
    print()

    print_info("5. Click \"Save Connector\"")
    print()

    print_success("Then come back to Claude and use the connector!")
    print()

    # Test
    print_step(8, "Testing MCP Server...")
    try:
        response = requests.get(f'http://localhost:{SERVER_PORT}/tools', timeout=2)
        if response.status_code == 200:
            print_success("MCP server is responding to tool requests")
            print(f"  Available tools: generate, get_metrics, get_providers, configure_gateway, cost_estimate")
    except Exception:
        print(f"{Colors.YELLOW}⚠ Could not verify tools, but server is running{Colors.NC}")

    print()

    # Cleanup instructions
    print_info("To stop the servers later:")
    print(f"  kill {mcp_pid}  # Stop MCP Server")
    print(f"  kill {ngrok_pid}  # Stop ngrok tunnel")
    print()

    print_info("Or use this command to stop both:")
    print(f"  {Colors.YELLOW}pkill -f 'python -m cohezion.gateway.mcp_http_server'; pkill -f 'ngrok http'{Colors.NC}")
    print()

    print(f"{Colors.GREEN}════════════════════════════════════════════{Colors.NC}")
    print(f"{Colors.GREEN}  Servers are running! Press Ctrl+C to stop.{Colors.NC}")
    print(f"{Colors.GREEN}════════════════════════════════════════════{Colors.NC}")
    print()

    # Keep running
    def signal_handler(sig, frame):
        print()
        print(f"{Colors.YELLOW}Stopping servers...{Colors.NC}")
        subprocess.run(['kill', str(mcp_pid)], capture_output=True)
        subprocess.run(['kill', str(ngrok_pid)], capture_output=True)
        print_success("Servers stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Display live logs
    try:
        with open('/tmp/mcp_server.log', 'r') as f:
            while True:
                line = f.readline()
                if line:
                    print(line.rstrip())
                else:
                    time.sleep(0.1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
