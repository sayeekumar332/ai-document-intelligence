# Engineering Log

This log records significant engineering work, observations, problems, and verification results.

## 2026-10-22 — Initial Development Environment Setup

### Objective

Establish a local Python development environment and Git repository for the AI Document Intelligence Platform.

### Environment Inspection

Commands executed:

```bash
sw_vers
uname -m
python3 --version
git --version
```

Observed results:

- macOS version reported as `27.0.1`.
- System architecture reported as `arm64`.
- Python reported as `3.12.3`.
- Git reported as `2.54.0`.

### Python Environment

The existing `py312` environment was inspected.

```bash
which python3
python3 -m pip --version
```

A separate project environment was created:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Verification confirmed Python `3.12.3` and pip `24.0` inside the project environment.

### Issue: Python Alias

The shell initially resolved `python` to `/opt/homebrew/bin/python3`, despite the project environment being activated.

Inspection showed that `python` was an alias.

Resolution:

```bash
unalias python
```

Verification confirmed that `python` resolved to `.venv/bin/python`.

Scope: the alias was removed for the current shell session only.

### Git Repository

The repository was inspected and initialized with:

```bash
git init -b main
```

Git reported an existing repository and reinitialized it. The repository was retained.

The first commit was created:

```text
2f3db98 chore: initialize AI document intelligence project
```

Files committed:

- `.gitignore`
- `README.md`

The initial working tree was verified as clean.

### Remote Configuration

The GitHub remote was configured as `origin`.

An initial URL was entered using Markdown link syntax. This was corrected to the plain URL:

```text
https://github.com/sayeekumar332/ai-document-intelligence.git
```

The final URL was verified with `git remote get-url origin`.

### Branching

The following feature branch was created:

```text
feat/project-configuration
```

The current branch was verified with `git branch --show-current`.

### Lessons Learned

1. A virtual environment should isolate project dependencies.
2. A shell alias can override the expected Python executable.
3. `type -a`, `which`, and `sys.executable` help diagnose interpreter selection.
4. `.gitignore` prevents local environment files from being tracked.
5. Git's hidden `.git` directory may exist even when a project appears empty in Finder.
6. Git remote URLs must be plain URLs, not Markdown links.
7. A feature branch keeps new development separate from `main`.

### Verification Status

Completed and verified:

- Python virtual environment creation and activation.
- Python and pip path verification.
- `.gitignore` creation and exclusion of `.venv/`.
- Initial Git commit.
- Git remote URL correction.
- Feature branch creation.

### Status at the end of initial project configuration

Completed:
- Project configuration in `pyproject.toml`.
- Python package scaffold and version test.
- pytest and Ruff installation.
- Package test execution.
- Ruff lint and formatting checks.
- Generated package metadata excluded through `.gitignore`.

Pending:
- PDF text extraction and its automated tests.
- Document chunking and retrieval.
- Local language-model integration.
- API and user interface.
- Continuous integration.
- Push of the feature branch and pull request.

Only move pending items to completed after verifying the actual result.
## 2026-10-22 — Python project configuration milestone

### Completed work

1. Created the initial repository and README.
2. Added development setup and Git workflow documentation.
3. Created `pyproject.toml` with project metadata, Python version
   requirements, development dependencies, pytest configuration, and
   Ruff linting and formatting rules.
4. Created the Python package at `src/ai_document_intelligence/`.
5. Added a package-version test in `tests/test_package.py`.
6. Installed the project in editable mode with `python -m pip install -e ".[dev]"`.
7. Installed pytest and Ruff as development tools.
8. Added `*.egg-info/` to `.gitignore` to exclude generated package metadata.

### Verification

- Python version: 3.12.3.
- pytest: the package-version test was collected and passed.
- Ruff lint check: passed.
- Ruff formatting check: passed; six files were already formatted.
- Git working tree: clean after the latest commit.
- Active branch: `feat/project-configuration`.

### Relevant commits

- `2f3db98` — Initial project setup.
- `45f79ff` — Development setup and Git workflow documentation.
- `35dcb7d` — Python package and quality-check configuration.
- `a4972f2` — Ignore generated Python package metadata.

### Engineering decisions and lessons

- Use a project-local virtual environment.
- Keep source code, tests, and documentation in separate directories.
- Use feature branches rather than developing directly on `main`.
- Run tests, linting, and formatting checks before committing.
- Exclude generated build metadata and local environment files from Git.
- Add runtime dependencies only when required by an implemented feature.

### Next planned feature

Implement local PDF text extraction with page-level source information,
automated tests, and explicit handling of invalid PDFs and PDFs without
extractable text. This feature has not yet been implemented.
