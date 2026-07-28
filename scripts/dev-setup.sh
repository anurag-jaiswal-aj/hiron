#!/usr/bin/env bash
# ==============================================================================
# HIRON PLATFORM LOCAL DEVELOPER SETUP SCRIPT
# ==============================================================================
# Verifies prerequisites and initializes local environment file.

set -euo pipefail

echo "=========================================="
echo " Hiron Platform — Developer Environment Check"
echo "=========================================="

# 1. Check Python
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version)
    echo "✓ Python: $PY_VER"
else
    echo "❌ Python 3 is not installed."
    exit 1
fi

# 2. Check Node.js
if command -v node >/dev/null 2>&1; then
    NODE_VER=$(node --version)
    echo "✓ Node.js: $NODE_VER"
else
    echo "❌ Node.js is not installed."
    exit 1
fi

# 3. Check pnpm
if command -v pnpm >/dev/null 2>&1; then
    PNPM_VER=$(pnpm --version)
    echo "✓ pnpm: $PNPM_VER"
else
    echo "❌ pnpm is not installed. Install via corepack or npm."
    exit 1
fi

# 4. Check Docker & Docker Compose
if command -v docker >/dev/null 2>&1; then
    DOCKER_VER=$(docker --version)
    echo "✓ Docker: $DOCKER_VER"
else
    echo "⚠️ Docker is not installed or not in PATH."
fi

# 5. Initialize .env.local
if [ ! -f .env.local ]; then
    cp .env.example .env.local
    echo "✓ Created .env.local from .env.example"
else
    echo "✓ .env.local already exists"
fi

echo "=========================================="
echo " Setup check complete. Run 'make dev' to start."
echo "=========================================="
