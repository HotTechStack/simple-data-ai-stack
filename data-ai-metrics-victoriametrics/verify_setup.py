#!/usr/bin/env python3
"""
Setup Verification Script

Checks that all components are properly configured before running the demo.
"""

import sys
import os
from pathlib import Path


def check_file_exists(filepath: str, required: bool = True) -> bool:
    """Check if a file exists"""
    exists = Path(filepath).exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    req_text = "(required)" if required else "(optional)"
    print(f"  {status} {filepath} {req_text}")
    return exists or not required


def check_docker() -> bool:
    """Check if Docker is available"""
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  ✓ Docker: {result.stdout.strip()}")
            return True
        else:
            print("  ✗ Docker not found")
            return False
    except Exception as e:
        print(f"  ✗ Docker check failed: {e}")
        return False


def check_docker_compose() -> bool:
    """Check if Docker Compose is available"""
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  ✓ Docker Compose: {result.stdout.strip()}")
            return True
        else:
            print("  ✗ Docker Compose not found")
            return False
    except Exception as e:
        print(f"  ✗ Docker Compose check failed: {e}")
        return False


def check_python_version() -> bool:
    """Check Python version"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"  ✓ Python: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ✗ Python {version.major}.{version.minor} (need 3.11+)")
        return False


def check_env_file() -> bool:
    """Check .env file and OpenAI key"""
    if not Path(".env").exists():
        print("  ⚠ .env file not found (optional for basic demo)")
        print("    Create from: cp .env.example .env")
        return False

    with open(".env", "r") as f:
        content = f.read()
        if "OPENAI_API_KEY" in content and "sk-" in content:
            print("  ✓ .env file exists with OpenAI key")
            return True
        else:
            print("  ⚠ .env exists but no valid OPENAI_API_KEY")
            print("    (Only needed for LLM features)")
            return False


def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("VictoriaMetrics Data Pipeline - Setup Verification")
    print("="*60 + "\n")

    all_passed = True

    # Check 1: Required files
    print("1. Checking required files...")
    required_files = [
        "docker-compose.yml",
        "pyproject.toml",
        "polars_pipeline.py",
        "duckdb_analytics.py",
        "llm_metrics_query.py",
        "grafana/dashboards/pipeline-observability.json",
        ".env.example",
        "README.md",
    ]

    for file in required_files:
        if not check_file_exists(file, required=True):
            all_passed = False

    # Check 2: Optional files
    print("\n2. Checking optional files...")
    optional_files = [
        ".env",
        "Makefile",
        "run_demo.sh",
        "QUICKSTART.md",
    ]

    for file in optional_files:
        check_file_exists(file, required=False)

    # Check 3: Docker
    print("\n3. Checking Docker...")
    if not check_docker():
        all_passed = False
        print("  → Install Docker: https://docs.docker.com/get-docker/")

    if not check_docker_compose():
        all_passed = False
        print("  → Docker Compose should be included with Docker Desktop")

    # Check 4: Python
    print("\n4. Checking Python...")
    if not check_python_version():
        all_passed = False
        print("  → Install Python 3.11+: https://www.python.org/downloads/")

    # Check 5: Environment
    print("\n5. Checking environment configuration...")
    check_env_file()

    # Check 6: Dependencies
    print("\n6. Checking Python dependencies...")
    try:
        import polars
        print(f"  ✓ polars {polars.__version__}")
    except ImportError:
        print("  ✗ polars not installed")
        all_passed = False

    try:
        import duckdb
        print(f"  ✓ duckdb {duckdb.__version__}")
    except ImportError:
        print("  ✗ duckdb not installed")
        all_passed = False

    try:
        import prometheus_client
        print(f"  ✓ prometheus_client installed")
    except ImportError:
        print("  ✗ prometheus_client not installed")
        all_passed = False

    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("✅ All checks passed! Ready to run.")
        print("\nNext steps:")
        print("  1. Start services:  docker compose up -d")
        print("  2. Run pipeline:    python polars_pipeline.py")
        print("  3. Open Grafana:    http://localhost:3000")
        print("\nOr use the quick start:")
        print("  ./run_demo.sh")
        print("  OR: make demo")
    else:
        print("⚠️  Some checks failed. See above for details.")
        print("\nTo fix:")
        print("  1. Install missing dependencies: uv sync")
        print("     (or: pip install -e .)")
        print("  2. Ensure Docker is running")
        print("  3. Create .env file: cp .env.example .env")

    print("="*60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
