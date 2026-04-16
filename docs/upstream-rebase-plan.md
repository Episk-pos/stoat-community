# Upstream History Rebase Plan

> **Status**: Planning  
> **Created**: 2026-04-14  
> **Epic**: upstream-rebase  

## Background

The upstream project (stoatchat) retroactively GPG-signed their entire commit
history on GitHub. This rewrote every commit hash while preserving identical tree
(content) objects. Our fork was created from the **pre-signing** history, so git
sees the two histories as unrelated (no common ancestor on backend) or partially
related (frontend shares the first 40 commits which pre-date the signing).

## Scope

Rebase our unique work onto `upstream/main` for both repos, starting with
**staging** (to validate via CI/deploy before touching production).

## Inventory

### stoat-backend (`/home/bwhite/Projects/stoat-backend`)

| Item | Value |
|------|-------|
| Remotes | `gl` = GitLab, `gh` = GitHub (ours), `upstream` = GitHub (stoatchat/stoatchat) |
| Merge base with upstream | **None** (different root commit hashes due to GPG rewrite) |
| Tree-matching commits | First **1,453** commits have identical trees |
| Our fork point (upstream SHA) | `b830631b` — "fix(docs): Update GitHub links (#647)" |
| Upstream commits since fork | **30** (up to `144e939c`) |
| Our unique commits (main) | **33** (CI, branding, features, Prometheus) |
| Our unique commits (staging) | **40** (main's 33 minus 6 Prometheus-only + 13 OAuth2/staging-specific) |
| Main-only commits (not in staging) | 6 — Prometheus instrumentation commits |
| Staging-only commits (not in main) | 13 — OAuth2 flow, staging CI, deploy fixes |

### stoat-frontend (`/home/bwhite/Projects/stoat-frontend`)

| Item | Value |
|------|-------|
| Remotes | `gl` = GitLab, `gh` = GitHub (ours), `upstream` = GitHub (stoatchat/for-web) |
| Merge base with upstream | `72f49297` (first 40 commits share actual hashes) |
| Tree-matching commits | First **1,625** commits have identical trees |
| Our fork point (upstream SHA) | `b169f945` — "feat: add automatic gain control to voice processing options (#953)" |
| Upstream commits since fork | **25** (up to `0b94704c`) |
| Our unique commits (main) | **60** (branding, CI, features, OAuth, debranding) |
| Our unique commits (staging) | **53** (overlaps heavily with main, plus staging-specific OAuth/CI) |
| Main-only commits (not in staging) | 14 — debranding, OG cards, voice fix, etc. |
| Staging-only commits (not in main) | 7 — staging OAuth, CI tweaks |

---

## Strategy

For each repo, we will:

1. **Create backup branches** of current main and staging
2. **Identify the upstream commit** that corresponds to our fork point
3. **Rebase our unique commits** onto `upstream/main` using `git rebase --onto`
4. **Do staging first** — push to GitLab, verify CI passes and deployment is healthy
5. **Then do main** — same process, push to GitLab

### Why rebase onto `upstream/main` tip (not fork point)?

Rebasing onto the tip of upstream/main brings us fully up to date with upstream
and gives us a clean base for submitting PRs back. The risk is conflicts with the
30 (backend) or 25 (frontend) new upstream commits, but these are manageable
numbers to resolve manually.

---

## Phase 1: Backend Staging

### Step 1.1 — Backup
```bash
cd /home/bwhite/Projects/stoat-backend
git branch backup/staging-pre-rebase staging
git branch backup/main-pre-rebase main
git push gl backup/staging-pre-rebase backup/main-pre-rebase
```

**Rollback**: `git checkout staging && git reset --hard backup/staging-pre-rebase`

### Step 1.2 — Create rebase branch
```bash
# Identify our fork point in the old (unsigned) history
# Our last tree-matching commit on staging is at position 1453
FORK_OLD=$(git rev-list --reverse staging | sed -n '1453p')
# The equivalent in upstream's (signed) history
FORK_NEW="b830631b"

# Create a temp branch from our unique staging commits
git checkout -b staging-rebased staging
```

### Step 1.3 — Rebase onto upstream/main
```bash
# Rebase everything after our fork point onto upstream/main tip
git rebase --onto upstream/main $FORK_OLD staging-rebased
```

This takes our 40 unique staging commits and replays them on top of
`upstream/main` (which is `144e939c`). Conflicts are expected in:
- README / docs (our branding vs upstream docs)
- CI files (our `.gitlab-ci.yml` vs their GitHub Actions)
- Cargo.toml / Cargo.lock (version differences)

**Resolve conflicts**: Keep our changes for branding/CI, take upstream for
everything else, then verify build compiles.

### Step 1.4 — Validate locally
```bash
# Check it compiles (if Rust toolchain available)
cargo check 2>&1 | head -50
# Or at minimum, verify the tree looks sane
git log --oneline -50 staging-rebased
git diff upstream/main..staging-rebased --stat
```

### Step 1.5 — Push staging to GitLab
```bash
# Unprotect main branch on GitLab (if needed)
# glab api -X PUT projects/:id/protected_branches/staging -f allow_force_push=true

git checkout staging
git reset --hard staging-rebased
git push gl staging --force-with-lease
```

**Rollback**: `git reset --hard backup/staging-pre-rebase && git push gl staging --force`

### Step 1.6 — Verify
- [ ] GitLab CI passes on staging
- [ ] Staging deployment completes successfully
- [ ] Staging environment is functional (basic smoke test)
- [ ] Wait at least 1 hour before proceeding to Phase 2

---

## Phase 2: Frontend Staging

Identical process to Phase 1 but for stoat-frontend.

### Step 2.1 — Backup
```bash
cd /home/bwhite/Projects/stoat-frontend
git branch backup/staging-pre-rebase staging
git branch backup/main-pre-rebase main
git push gl backup/staging-pre-rebase backup/main-pre-rebase
```

### Step 2.2 — Create rebase branch
```bash
FORK_OLD=$(git rev-list --reverse staging | sed -n '1625p')
FORK_NEW="b169f945"

git checkout -b staging-rebased staging
```

### Step 2.3 — Rebase onto upstream/main
```bash
git rebase --onto upstream/main $FORK_OLD staging-rebased
```

Expected conflicts:
- Package.json / lockfile
- Branding assets and i18n files
- CI configuration
- OAuth/auth components

### Step 2.4 — Validate locally
```bash
pnpm install
pnpm build 2>&1 | tail -20
```

### Step 2.5 — Push staging to GitLab
```bash
git checkout staging
git reset --hard staging-rebased
git push gl staging --force-with-lease
```

### Step 2.6 — Verify
- [ ] GitLab CI passes on staging
- [ ] Frontend staging deployment is healthy
- [ ] Can log in and use basic features
- [ ] Wait at least 1 hour before proceeding

---

## Phase 3: Backend Main

Only proceed after Phase 1 staging is verified.

### Step 3.1 — Rebase main
```bash
cd /home/bwhite/Projects/stoat-backend
FORK_OLD=$(git rev-list --reverse main | sed -n '1453p')

git checkout -b main-rebased main
git rebase --onto upstream/main $FORK_OLD main-rebased
```

Main has 33 unique commits. Most overlap with staging (which we already
resolved), so conflicts should be minimal or identical.

### Step 3.2 — Push main to GitLab
```bash
# Unprotect if needed
git checkout main
git reset --hard main-rebased
git push gl main --force-with-lease
# Re-protect
```

### Step 3.3 — Verify
- [ ] CI passes on main
- [ ] Production deployment completes
- [ ] Production is functional

---

## Phase 4: Frontend Main

Only proceed after Phase 2 staging is verified.

### Step 4.1 — Rebase main
```bash
cd /home/bwhite/Projects/stoat-frontend
FORK_OLD=$(git rev-list --reverse main | sed -n '1625p')

git checkout -b main-rebased main
git rebase --onto upstream/main $FORK_OLD main-rebased
```

### Step 4.2 — Push main to GitLab
```bash
git checkout main
git reset --hard main-rebased
git push gl main --force-with-lease
```

### Step 4.3 — Verify
- [ ] CI passes
- [ ] Production deployment OK
- [ ] Functional smoke test passes

---

## Phase 5: Cleanup

```bash
# Both repos: push updated main/staging to GitHub mirror
cd /home/bwhite/Projects/stoat-backend
git push gh main --force-with-lease
git push gh staging --force-with-lease

cd /home/bwhite/Projects/stoat-frontend
git push gh main --force-with-lease
git push gh staging --force-with-lease

# Verify: can we now create a PR to upstream?
# git checkout -b test/pr-check upstream/main
# (should share common history with upstream/main)
```

After verification, backup branches can be deleted:
```bash
git branch -D backup/staging-pre-rebase backup/main-pre-rebase
git push gl --delete backup/staging-pre-rebase backup/main-pre-rebase
```

---

## Rollback Plan (at any phase)

If anything goes wrong at any point:

```bash
# Backend
cd /home/bwhite/Projects/stoat-backend
git checkout staging && git reset --hard backup/staging-pre-rebase
git checkout main && git reset --hard backup/main-pre-rebase
git push gl staging main --force

# Frontend
cd /home/bwhite/Projects/stoat-frontend
git checkout staging && git reset --hard backup/staging-pre-rebase
git checkout main && git reset --hard backup/main-pre-rebase
git push gl staging main --force
```

This restores the exact state before we started. The backup branches on GitLab
serve as a remote safety net.

---

## Key Risks

1. **Rebase conflicts** — Most likely in branding, CI, and dependency files.
   Mitigation: resolve carefully, verify build after each.
2. **Submodule issues (frontend)** — stoat.js submodule may need updating.
   Mitigation: check submodule state after rebase.
3. **Production deployment on main push** — This is why we do staging first.
4. **GitLab branch protection** — May need to temporarily unprotect branches.
   Mitigation: use GitLab API to unprotect/reprotect programmatically.
5. **Other developers' local branches** — Anyone with local branches based on
   the old history will need to rebase. Document this.

## Reference SHAs

These are the critical commit hashes for the rebase operations:

**Backend:**
- Fork point (our history): `30ba35a1` (position 1453 on main/staging)
- Fork point (upstream history): `b830631b`
- Upstream main tip: `144e939c`

**Frontend:**
- Fork point (our history): `0e230657` (position 1625 on main/staging)  
- Fork point (upstream history): `b169f945`
- Upstream main tip: `0b94704c`
