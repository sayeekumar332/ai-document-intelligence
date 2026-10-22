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
git diff --staged
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

## 8. Merge Policy

The intended policy is to merge feature branches into `main` through pull requests after the relevant checks pass.

Where GitHub repository settings support branch protection or rulesets, configure appropriate restrictions for `main`. These settings must be verified in GitHub; this document does not imply that protection is already enabled.
