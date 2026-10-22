# Development Environment Setup

## 1. Purpose

This document records the local development environment and setup decisions for the AI Document Intelligence Platform.

The project is being developed on macOS using Python, Git, and a project-specific virtual environment.

## 2. Development Environment

| Component | Verified configuration |
|---|---|
| Operating system | macOS |
| System architecture | `arm64` |
| Python version | Python 3.12.3 |
| Python version manager | pyenv |
| Project virtual environment | `.venv/` |
| Version control | Git |
| Default branch | `main` |
| Remote repository | `https://github.com/sayeekumar332/ai-document-intelligence.git` |

The architecture output `arm64` confirms an ARM-based environment; it does not, by itself, identify the exact Apple processor model.

## 3. Python Environment Isolation

The existing Python environment is located at `/Users/sayeekumars/py312`.

A separate virtual environment was created for this project to isolate its dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

The project environment was verified using:

```bash
./.venv/bin/python --version
./.venv/bin/python -m pip --version
```

Verified results:

- Python: `3.12.3`
- pip: `24.0`
- Environment location: project-local `.venv/`

## 4. Shell Alias Troubleshooting

Initially, `python` was configured as a shell alias pointing to `/opt/homebrew/bin/python3`. This alias could bypass the project virtual environment.

The alias was removed for the current shell session:

```bash
unalias python
```

The following commands then confirmed that Python and pip were using `.venv`:

```bash
which python
python --version
python -m pip --version
```

The alias removal was session-specific; permanent shell configuration was not changed.

## 5. Git Repository Setup

The repository uses `main` as its default branch.

The following command was used to initialize Git:

```bash
git init -b main
```

Git reported that the repository already existed and was reinitialized. The existing repository was retained rather than deleted or recreated.

The initial commit contains:

- `.gitignore`
- `README.md`

The initial commit was recorded as:

`2f3db98 chore: initialize AI document intelligence project`

## 6. Git Ignore Rules

The `.gitignore` file excludes:

- Python virtual environments
- Python bytecode and caches
- Test and lint caches
- Environment files containing configuration or secrets
- macOS `.DS_Store` files
- Local data and generated artifacts

The virtual environment is not intended to be committed. Project dependencies will be recorded separately in the project's dependency configuration.

## 7. Remote Repository

The configured Git remote is named `origin`.

```text
https://github.com/sayeekumar332/ai-document-intelligence.git
```

The remote URL was verified using:

```bash
git remote get-url origin
```

The URL must be a plain Git URL, without Markdown link syntax.

## 8. Branching Strategy

The current development branch is:

`feat/project-configuration`

The intended workflow is:

1. Create a feature branch from the appropriate base branch.
2. Implement a focused change.
3. Update relevant documentation.
4. Run automated checks.
5. Push the feature branch.
6. Open a pull request.
7. Merge after review and required checks.

The initial setup commit on `main` is retained as the repository baseline. Subsequent development is intended to take place on feature branches.

## 9. Reproducibility and Security

- Keep the virtual environment out of version control.
- Record project dependencies in version-controlled configuration files.
- Never commit API keys, passwords, tokens, or private documents.
- Document commands and verify their results.
- Do not claim a test or validation succeeded until it has actually been run.

## 10. Current Status

Completed:
- Local Python virtual environment created and activated.
- Python and pip paths verified.
- Git repository and initial commit established.
- `.gitignore` and initial `README.md` committed.
- GitHub remote URL configured.
- `feat/project-configuration` branch created.

Not yet completed:
- Python project configuration.
- Automated test setup.
- Linting and formatting checks.
- Application implementation.
- Continuous integration.
- Initial feature-branch push and pull request.

This status must be updated as work progresses.