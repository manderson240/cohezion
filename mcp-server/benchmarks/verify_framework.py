#!/usr/bin/env python3
"""
Verify that the benchmarking framework is properly set up and ready to run.

This script checks:
1. Python dependencies are installed
2. Framework modules are importable
3. MCP server is accessible
4. Output directories exist
5. Required tools are available
"""

import sys
import subprocess
from pathlib import Path

# Colors
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'


def check_python_version():
    """Verify Python 3.9+"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"{GREEN}✓{RESET} Python {version.major}.{version.minor} (required: 3.9+)")
        return True
    else:
        print(f"{RED}✗{RESET} Python {version.major}.{version.minor} (required: 3.9+)")
        return False


def check_dependencies():
    """Verify required packages."""
    required = {
        'aiohttp': 'Async HTTP client',
        'psutil': 'System monitoring',
    }

    all_ok = True
    for package, description in required.items():
        try:
            __import__(package)
            print(f"{GREEN}✓{RESET} {package}: {description}")
        except ImportError:
            print(f"{RED}✗{RESET} {package}: {description}")
            print(f"  Install with: pip install {package}")
            all_ok = False

    return all_ok


def check_framework_files():
    """Verify benchmark framework files exist."""
    benchmark_dir = Path(__file__).parent
    files = {
        'benchmark_framework.py': 'Main benchmark framework',
        'run_benchmarks.sh': 'Orchestration script',
        'requirements.txt': 'Dependencies list',
        'verify_framework.py': 'This verification script',
    }

    all_ok = True
    for filename, description in files.items():
        filepath = benchmark_dir / filename
        if filepath.exists():
            print(f"{GREEN}✓{RESET} {filename}: {description}")
        else:
            print(f"{RED}✗{RESET} {filename}: {description} (MISSING)")
            all_ok = False

    return all_ok


def check_output_directories():
    """Verify output directories."""
    benchmark_dir = Path(__file__).parent
    output_dirs = {
        benchmark_dir: 'Benchmark directory',
        benchmark_dir / 'results': 'Results subdirectory (optional)',
    }

    all_ok = True
    for dirpath, description in output_dirs.items():
        if dirpath.exists() and dirpath.is_dir():
            print(f"{GREEN}✓{RESET} {dirpath.name}: {description}")
        elif description.endswith('(optional)'):
            print(f"{YELLOW}ℹ{RESET} {dirpath.name}: {description} (will be created)")
        else:
            print(f"{RED}✗{RESET} {dirpath.name}: {description} (MISSING)")
            all_ok = False

    return all_ok


def check_mcp_server():
    """Verify MCP server connectivity."""
    try:
        import urllib.request
        response = urllib.request.urlopen('http://localhost:8000/health', timeout=2)
        if response.status == 200:
            print(f"{GREEN}✓{RESET} MCP server: Running at http://localhost:8000")
            return True
        else:
            print(f"{RED}✗{RESET} MCP server: Not responding correctly ({response.status})")
            return False
    except Exception as e:
        print(f"{YELLOW}⚠{RESET} MCP server: Not accessible at http://localhost:8000")
        print(f"  {str(e)}")
        print(f"  Start MCP server before running benchmarks")
        return False


def check_shell_tools():
    """Verify required shell tools."""
    tools = {
        'python3': 'Python interpreter',
        'curl': 'HTTP client (for health checks)',
        'jq': 'JSON processor (optional)',
    }

    all_ok = True
    for tool, description in tools.items():
        result = subprocess.run(
            ['which', tool],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"{GREEN}✓{RESET} {tool}: {description}")
        elif description.endswith('(optional)'):
            print(f"{YELLOW}ℹ{RESET} {tool}: {description} (not found)")
        else:
            print(f"{RED}✗{RESET} {tool}: {description} (MISSING)")
            all_ok = False

    return all_ok


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("Benchmarking Framework Verification")
    print("=" * 70)
    print()

    checks = [
        ("Python Version", check_python_version),
        ("Python Dependencies", check_dependencies),
        ("Framework Files", check_framework_files),
        ("Output Directories", check_output_directories),
        ("Shell Tools", check_shell_tools),
        ("MCP Server", check_mcp_server),
    ]

    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"{RED}✗{RESET} Error during check: {e}")
            results.append((name, False))

    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status}: {name}")

    print()
    if passed == total:
        print(f"{GREEN}✓ All checks passed!{RESET}")
        print(f"\nReady to run benchmarks:")
        print(f"  ./run_benchmarks.sh")
        return 0
    else:
        print(f"{RED}✗ {total - passed} check(s) failed{RESET}")
        print(f"\nTo run benchmarks, fix the failures above and verify:")
        print(f"  1. MCP server is running: python3 -m kyutai_mcp.main")
        print(f"  2. Dependencies installed: pip install -r requirements.txt")
        print(f"  3. Re-run verification: python3 verify_framework.py")
        return 1


if __name__ == '__main__':
    sys.exit(main())
