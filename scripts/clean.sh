#!/usr/bin/env bash
# ==============================================================================
# HIRON PLATFORM CLEANUP SCRIPT
# ==============================================================================
# Removes build artifacts, coverage data, and temporary cache directories.

set -euo pipefail

echo "Cleaning temporary caches and build artifacts..."

rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov .next dist build .turbo
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name "*.egg-info" -exec rm -rf {} +

echo "Cleanup completed."
