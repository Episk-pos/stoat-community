# Upstream Git Workflow for Forked Repositories

## Overview

The Episkopos project maintains forks of two Stoat repositories. We need a clear separation between our modifications (branding, features, integrations) and the upstream codebase so that:

- **Diffing is easy** — `git log upstream..main --oneline` shows exactly what we've changed.
- **Upstream contributions flow cleanly** — changes we want to contribute back can be cherry-picked or PR'd against upstream without carrying our local-only modifications.
- **Syncing stays smooth** — upstream updates merge into our branch with minimal conflict surface because we know precisely where our divergence lives.

This document describes the branch structure, remotes, and day-to-day git operations for working with these forked repos.

## Branch Structure

| Branch | Purpose | Rules |
|--------|---------|-------|
| `upstream` | Mirrors the upstream repo's `main` branch | Never commit directly. Updated via fetch + fast-forward merge only. |
| `main` | Our production branch | CI must pass. Receives merges from `upstream` and feature branches. May auto-deploy. |
| `staging` | Integration testing (if applicable) | Used for pre-production validation before merging to `main`. |
| Feature branches | All development work | Prefixed with `feat/`, `fix/`, or `chore/`. Branched from `main`, merged back to `main`. |

### Branch relationships

```
upstream repo main
       │
       ▼
   [upstream]  ──(merge)──▶  [main]  ◀──(merge)──  feat/my-feature
                                │
                                ▼
                           [staging]  (optional)
```

## Remotes

Each forked repo is configured with three remotes:

| Remote | Host | Purpose |
|--------|------|---------|
| `upstream` | GitHub (stoatchat org) | The original upstream repo. Read-only for us. |
| `gl` | GitLab (work.episkopos.community) | Our primary remote. CI/CD runs here. |
| `gh` | GitHub (Episk-pos org) | Our GitHub mirror. Used for upstream PRs. |

To verify your remotes:

```bash
git remote -v
```

Expected output (example for stoat-frontend):

```
gh       git@github.com:Episk-pos/for-web.git (fetch)
gh       git@github.com:Episk-pos/for-web.git (push)
gl       git@work.episkopos.community:episkopos/stoat-frontend.git (fetch)
gl       git@work.episkopos.community:episkopos/stoat-frontend.git (push)
upstream git@github.com:stoatchat/for-web.git (fetch)
upstream git@github.com:stoatchat/for-web.git (push)
```

## Common Operations

### Syncing the upstream branch

Pull the latest changes from the upstream repo into our `upstream` branch. This should be done regularly (daily or before starting work that depends on upstream).

```bash
git fetch upstream main
git checkout upstream
git merge upstream/main --ff-only
git push gl upstream
git push gh upstream
```

The `--ff-only` flag ensures the merge is a fast-forward. If it fails, something has been committed directly to the `upstream` branch — investigate and fix before proceeding.

### Starting a new feature

```bash
git checkout main
git pull gl main
git checkout -b feat/my-feature
```

### Merging upstream changes into main

After syncing the `upstream` branch, merge it into `main` to pick up new upstream changes:

```bash
git checkout main
git pull gl main
git merge upstream --no-ff -m "merge: sync upstream changes"
git push gl main
git push gh main
```

The `--no-ff` flag creates a merge commit so the sync point is visible in history.

### Checking divergence

See what changes we have that upstream does not:

```bash
git log upstream..main --oneline
```

See what upstream changes we haven't merged yet:

```bash
git log main..upstream --oneline
```

See a full diff of our divergence:

```bash
git diff upstream..main
```

## Upstream Contribution Flow

When a change is suitable for contributing back to the upstream Stoat project:

1. **Create a feature branch** from `main` as usual.
2. **Develop and test** the change.
3. **Merge into our `main`** via merge request on GitLab.
4. **Open a PR against the upstream repo** on GitHub (from our `gh` fork to `upstream`).
5. **If upstream accepts**, the change will flow back into our `upstream` branch on the next sync — the merge into `main` will then be a no-op for that code.

When preparing an upstream PR, keep the branch clean of any local-only changes (branding, config, etc.). If the feature branch contains mixed changes, create a separate branch with only the upstream-bound commits.

## Local-Only Changes

Some changes are intentionally not contributed upstream. These include:

- **Branding** — logos, colors, product naming (Censer, Unveil, Postern)
- **License compliance** — AGPL headers, attribution
- **Integrations** — Episkopos-specific features, API endpoints, auth providers
- **Configuration** — environment-specific defaults

For local-only changes:

1. Create a feature branch as normal (`feat/`, `fix/`, `chore/`).
2. Merge into our `main` only.
3. Do **not** open an upstream PR.
4. Document in the commit message that the change is intentionally local-only, for example:

```
feat: add Episkopos branding to login page

Local-only change — not intended for upstream contribution.
```

This makes it clear when reviewing `git log upstream..main` which commits are divergence by design.

## Applicable Repositories

| Our repo | Upstream repo | Description |
|----------|---------------|-------------|
| `stoat-frontend` (gl: `episkopos/stoat-frontend`) | [stoatchat/for-web](https://github.com/stoatchat/for-web) | Web frontend (React/Vite) |
| `stoat-backend` (gl: `episkopos/stoat-backend`) | [stoatchat/stoatchat](https://github.com/stoatchat/stoatchat) | Backend services (Rust: Delta, Bonfire, Autumn, January) |
