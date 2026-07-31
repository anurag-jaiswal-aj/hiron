# Contributing to Hiron

Welcome! We are excited that you are interested in contributing to Hiron. This guide will help you get set up and understand our development process.

---

## 🛠️ Development Setup

1. **Fork and clone the repository**:

   ```bash
   git clone https://github.com/<your-username>/hiron.git
   cd hiron
   ```

2. **Initialize local environment**:

   ```bash
   make setup
   ```

3. **Install Python dependencies**:

   ```bash
   uv sync --all-extras
   ```

4. **Install Node dependencies**:
   ```bash
   pnpm install
   ```

---

## 🌿 Branch Naming

Use clear prefix conventions for all contribution branches:

- `feat/feature-name` — New features
- `fix/bug-description` — Bug fixes
- `docs/doc-update` — Documentation improvements
- `refactor/scope-description` — Code refactoring without behavior changes
- `test/test-description` — Test additions or improvements

---

## 📝 Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```text
<type>(<scope>): <short summary>

[optional body]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

**Example**:

```text
feat(scores): add recommendation score threshold validation
```

---

## 🧪 Running Tests

Ensure all automated tests pass before submitting a Pull Request:

```bash
# Run complete Python test suite
uv run pytest

# Run specific test file
uv run pytest apps/api/tests/test_e2e_full_recruitment_workflow.py
```

---

## 🎨 Linting & Formatting

All code must pass static type checking and formatting rules:

```bash
# Python formatting & linter checks
uv run ruff format --check .
uv run ruff check .

# MyPy strict type check
uv run mypy apps/api

# Markdown and JSON Prettier check
npx prettier --check "**/*.{json,yaml,yml,md}"
```

To automatically format files locally:

```bash
uv run ruff format .
npx prettier --write "**/*.{json,yaml,yml,md}"
```

---

## 🚀 Pull Request Process

1. Create a descriptive branch from `main`.
2. Keep Pull Requests focused on a single responsibility.
3. Ensure all tests (`uv run pytest`), MyPy strict type checks, Ruff, and Prettier pass cleanly.
4. Submit the PR against `main` with a clear explanation of changes and linked issues.

---

## 🐛 Reporting Bugs

If you find a bug:

1. Search existing issues to avoid duplicates.
2. Open a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, Docker version)

---

## 📜 Code of Conduct

All contributors are expected to uphold a welcoming, respectful, and professional environment. Please refer to our engineering standards in [`docs/ENGINEERING_GUIDELINES.md`](./docs/ENGINEERING_GUIDELINES.md).
