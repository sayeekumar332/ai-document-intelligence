# Git Workflow

## 1. Objective

Use a traceable, reviewable Git workflow for the AI Document Intelligence Platform.

## 2. Branches

- `main`: stable project history.
- `feat/<name>`: new functionality.
- `fix/<name>`: bug fixes.
- `test/<name>`: test-focused changes.
- `docs/<name>`: documentation-only changes.
- `ci/<name>`: continuous integration changes.

Branch names should describe the work being performed.

Examples:

- `feat/pdf-ingestion`
- `feat/semantic-retrieval`
- `fix/empty-document-handling`
- `test/retrieval-regression`
- `docs/architecture-overview`
- `ci/python-test-workflow`

## 3. Development Procedure

1. Confirm the current branch and working-tree state.
2. Create a branch for the task.
3. Implement a focused change.
4. Add or update tests where applicable.
5. Update documentation.
6. Run the relevant tests and quality checks.
7. Review the changes using Git.
8. Commit the verified work.
9. Push the branch to GitHub.
10. Open a pull request.
11. Merge only after the required checks and review are complete.

## 4. Useful Commands

Inspect the working tree:

```bash
git status --short --branch
```

Inspect the current branch:

```bash
git branch --show-current
```

Create a feature branch:

```bash
git switch -c feat/example-feature
```

Review changes:

```bash
git diff
git diff --cached
```

Stage specific files:

```bash
git add path/to/file
```

Commit a change:

```bash
git commit -m "feat: describe the change"
```

Push a new branch:

```bash
git push -u origin feat/example-feature
```
Review a specific file:

```bash
git diff -- path/to/file
```

Summarize unstaged changes:

```bash
git diff --stat
```

Check staged changes for whitespace errors before committing:

```bash
git diff --cached --check
```

Review recent commits:

```bash
git log -5 --oneline
```

Switch to an existing branch:

```bash
git switch branch-name
```


## 5. Commit Message Convention

Use a concise type prefix and a descriptive message.

Examples:

- `feat: add PDF text extraction`
- `fix: handle empty PDF documents`
- `test: cover unsupported file types`
- `refactor: isolate retrieval logic`
- `docs: document development setup`
- `ci: run tests on pull requests`
- `chore: configure development tooling`

The message must accurately describe the change.

## 6. Pull Request Requirements

A pull request should describe:

- The problem or requirement.
- The implementation approach.
- Relevant design decisions.
- Tests and checks executed.
- Known limitations.
- Documentation changes.

A pull request must not claim that checks passed unless they were executed and passed.

For a solo-developed project, the author should perform a deliberate self-review. Independent review should be claimed only when another person has actually reviewed the changes.

## 7. Repository Safety

- Never commit `.venv/`.
- Never commit credentials or API keys.
- Keep sensitive source documents out of public repositories.
- Do not force-push or overwrite remote history without a justified, understood reason.
- Inspect remote state before pushing if the remote may already contain commits.
- Keep changes focused and easy to review.
- Never commit local .env files or other files containing secrets.
- Keep generated files, temporary test artifacts, and local-only datasets out of Git unless explicitly required.
- Never add the local reference PDF used for integration testing to the public repository.

## 8. Merge Policy

The intended policy is to merge feature branches into `main` through pull requests after the relevant checks pass.

Where GitHub repository settings support branch protection or rulesets, configure appropriate restrictions for `main`. These settings must be verified in GitHub; this document does not imply that protection is already enabled.

After a pull request is merged, synchronize the local main branch with origin/main before creating the next task branch.

## 9. Feature Branch to Pull Request Workflow

Follow this procedure for every new feature or documentation change.

### Step 1: Synchronize with the latest main branch

Start with a clean working tree. If uncommitted changes exist, review and preserve them before switching branches.

```bash
git status --short --branch
git switch main
git pull --ff-only origin main
git status --short --branch
```

Confirm that the working tree is clean before proceeding.

### Step 2: Create a dedicated branch

Create the branch from the updated `main` branch.

```bash
git switch -c feat/example-feature
```

Use the appropriate prefix for the work:

- `feat/` for new functionality.
- `fix/` for bug fixes.
- `test/` for test-focused changes.
- `docs/` for documentation-only changes.
- `ci/` for continuous integration changes.

### Step 3: Implement and validate the change

Keep the change focused. Add or update tests and documentation where applicable.

Run the project's standard quality checks:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
git diff --check
```

Run any feature-specific integration tests as well. For real-PDF integration tests, configure `REFERENCE_PDF_PATH` to point to the local reference PDF when required. Never add the private or reference PDF to the repository.

Record only checks that were actually executed and passed.

### Step 4: Review and stage the changes

Inspect the changes before staging:

```bash
git status --short
git diff
git diff --stat
```

Stage only the intended files:

```bash
git add path/to/file
```

Review the staged changes:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached
git status --short
```

Check for accidental inclusion of credentials, private documents, generated files, or unrelated changes.

### Step 5: Commit and push

Commit the verified changes using the project's commit message convention.

```bash
git commit -m "docs: document complete Git workflow"
git push -u origin docs/update-gitflow-workflow
```

For subsequent commits on the same branch, use:

```bash
git push
```

### Step 6: Open and merge a pull request

On GitHub:

1. Open a pull request from the working branch into `main`.
2. Describe the requirement, implementation, design decisions, tests, limitations, and documentation changes.
3. Review the diff and inspect the available automated check results.
4. Merge only after the required checks pass and the review is complete.

For solo development, perform a deliberate self-review. Do not claim an independent review unless another person performed it.

### Step 7: Synchronize local main after merging

After the pull request has been merged on GitHub:

```bash
git switch main
git pull --ff-only origin main
git status --short --branch
```

Confirm that local `main` contains the merged changes and the working tree is clean.

### Step 8: Start the next task

Create the next task branch from the updated `main` branch. Do not base new work on a stale local `main` branch.

Example:

```bash
git switch -c feat/local-semantic-retrieval
```

### Workflow rules

- Do not commit directly to `main`.
- Use a dedicated branch for each task.
- Run relevant tests and quality checks before committing.
- Review staged changes before committing.
- Use pull requests to merge changes into `main`.
- Synchronize local `main` after each merge.
- Keep private documents, credentials, and local environment files out of Git.
- Update tests and documentation when the feature changes their behavior or design.
