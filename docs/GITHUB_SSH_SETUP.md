# GitHub SSH Authentication Setup on macOS

## 1. Purpose

This document explains how to configure SSH authentication between a macOS development machine and GitHub for Git operations such as `clone`, `fetch`, `pull`, and `push`.

The procedure was tested during the initial configuration of the AI Document Intelligence Platform repository.

## 2. Why SSH Authentication?

GitHub does not accept ordinary account passwords for Git operations over HTTPS.

SSH authentication uses a cryptographic key pair:

- **Private key:** Remains on the developer's computer and must never be shared.
- **Public key:** Can be registered with GitHub.
- **SSH agent:** Makes a loaded private key available to SSH authentication.
- **Git remote:** Specifies the repository address used for fetch and push operations.

An SSH key authenticates the developer, but repository permissions still determine which operations are authorized.

## 3. Inspect Existing SSH Keys

List the contents of the SSH directory:

```bash
ls -al ~/.ssh
```

An existing Ed25519 key pair typically contains:

```text
id_ed25519
id_ed25519.pub
```

The files have different purposes:

| File | Purpose | Handling |
|---|---|---|
| `id_ed25519` | Private key | Keep secret |
| `id_ed25519.pub` | Public key | May be registered with GitHub |
| `known_hosts` | Records trusted SSH server identities | Do not edit without understanding the implications |

If a suitable key pair already exists, inspect and test it before creating another one.

## 4. Start the SSH Agent and Load the Key

Start an SSH agent:

```bash
eval "$(ssh-agent -s)"
```

Add the existing Ed25519 key and integrate it with the macOS Keychain:

```bash
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

A successful operation reports that the identity was added.

If the key is protected by a passphrase, enter that passphrase when prompted. Never disclose it in documentation, source control, or chat messages.

## 5. Test GitHub Authentication

Run:

```bash
ssh -T git@github.com
```

A successful authentication produces a message similar to:

```text
Hi YOUR_GITHUB_USERNAME! You've successfully authenticated, but GitHub does not provide shell access.
```

This confirms that GitHub recognizes the SSH identity.

GitHub does not provide interactive shell access through this connection; that message is normal.

If GitHub does not recognize the key, follow Section 6.

## 6. Register the Public Key with GitHub

First, copy the public key:

```bash
pbcopy < ~/.ssh/id_ed25519.pub
```

Then:

1. Open https://github.com/settings/keys
2. Select **New SSH key**.
3. Enter a descriptive title, such as `MacBook Air`.
4. Select **Authentication Key**.
5. Paste the copied public key.
6. Save the key.

Only the `.pub` file should be copied into GitHub.

**Never upload or share `~/.ssh/id_ed25519`, which is the private key.**

After registration, test again:

```bash
ssh -T git@github.com
```

If authentication still fails, inspect the SSH agent and verify that the correct public key is registered.

## 7. Configure the Repository's SSH Remote

For this project, the repository is:

```text
sayeekumar332/ai-document-intelligence
```

Set the remote URL to SSH:

```bash
git remote set-url origin git@github.com:sayeekumar332/ai-document-intelligence.git
```

Verify the configuration:

```bash
git remote -v
```

Expected output:

```text
origin  git@github.com:sayeekumar332/ai-document-intelligence.git (fetch)
origin  git@github.com:sayeekumar332/ai-document-intelligence.git (push)
```

The `origin` name is a local alias for the remote repository. Changing its URL does not create a new branch or modify existing commits.

## 8. Push a Feature Branch

Check the current branch and working-tree state:

```bash
git status --short --branch
git branch --show-current
```

Push the project-configuration branch:

```bash
git push -u origin feat/project-configuration
```

The `-u` option sets the upstream tracking branch. Future pushes from that branch can normally use:

```bash
git push
```

A successful push confirms that GitHub accepted the branch and commits.

Pushing a feature branch does not automatically merge it into `main`.

## 9. Verify the Final Configuration

Run:

```bash
git remote -v
git branch -vv
git status --short --branch
git log -6 --oneline
ssh -T git@github.com
```

Verify the following:

- The remote uses the SSH URL.
- The feature branch tracks its corresponding remote branch.
- The working tree is clean, if all changes have been committed.
- The expected commits appear in the log.
- GitHub recognizes the SSH key.

## 10. Troubleshooting

### HTTPS authentication failed

Error:

```text
Password authentication is not supported for Git operations.
```

Cause: GitHub does not accept ordinary account passwords for Git operations over HTTPS.

Resolution: Configure SSH authentication or use an appropriately scoped personal access token over HTTPS.

### SSH authentication failed

Check whether the key is loaded:

```bash
ssh-add -l
```

Check whether GitHub accepts the key:

```bash
ssh -T git@github.com
```

If needed, register the public key through GitHub's SSH key settings.

### Push permission denied

Successful SSH authentication does not guarantee write access to a particular repository. Verify the repository URL, account identity, and repository permissions.

### Remote contains commits not present locally

Do not force-push automatically. Inspect the remote history and reconcile the branches deliberately before pushing.

### Host authenticity prompt

When connecting to GitHub for the first time, SSH may ask whether to trust the host. Verify the displayed fingerprint against GitHub's official documentation before accepting it:

https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints

## 11. Security Rules

1. Never commit private SSH keys.
2. Never publish private keys, passphrases, access tokens, or credentials.
3. Register only the intended public key.
4. Do not disable SSH host-key verification to bypass connection problems.
5. Use repository permissions appropriate to the work being performed.
6. If a private key is exposed, revoke or replace the affected credential promptly.
7. Keep sensitive documents and credentials out of public repositories.

## 12. Project-Specific Record

During the initial project setup:

- An existing Ed25519 SSH key pair was found.
- The private key was loaded into the SSH agent using the macOS Keychain option.
- GitHub authentication succeeded for the configured account.
- The repository remote was changed from HTTPS to SSH.
- The `feat/project-configuration` branch was pushed successfully.
- Upstream tracking was configured for `origin/feat/project-configuration`.

The successful push verified that the configured identity had sufficient access to publish that branch at the time of the operation.

## 13. References

- GitHub SSH key setup: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
- GitHub SSH key management: https://github.com/settings/keys
- GitHub SSH fingerprints: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
