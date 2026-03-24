# Knowledge Browser Integration Plan

> Integrate the Knowledge Browser (Elixir/Phoenix) into the stoat-community dev
> environment so all chat-related services run in one Tilt stack.

## Goal

Package Stoat (chat), Knowledge Browser, and Discord-Stoat sync as a unified
multi-tenant offering. The dev environment should reflect this by having all
pieces available in one Tilt stack.

## Approach

### Config & Toggle

- Use a `dev-config.yaml` file (auto-generated with defaults if missing)
- Knowledge Browser starts **disabled** by default
- Users enable via:
  - `tilt args -- --knowledge-browser` (live toggle, no restart)
  - `tilt up -- --knowledge-browser` (one-time)
  - Edit `dev-config.yaml` + restart (persistent)
  - Tilt UI button (if UIButton API works — see experiment branch)

### Tiltfile Changes (`dev/Tiltfile`)

Add `config.define_bool('knowledge-browser')` and a new section at the bottom:

**When disabled**: Show a `local_resource` with instructions for enabling.

**When enabled but repo not cloned**: Show a clone button that clones
`knowledge-browser` as a sibling repo.

**When enabled and cloned**:
1. `docker_build('kb-app', KB_PATH, ...)` with live_update (same pattern as
   KB's own Tiltfile — sync lib/, config/, priv/, assets/)
2. Deploy KB postgres + app into the `censer` KinD cluster's `censer` namespace
3. Wire up `k8s_resource` with:
   - Port forward `4002:4000` for KB web UI
   - Labels `['knowledge-browser']`
   - `resource_deps` on KB postgres
4. Set env vars on the KB deployment:
   - `DATABASE_URL` → KB's own postgres (`kb-postgres.censer.svc:5432`)
   - `STOAT_MONGO_URL` → `mongodb://mongodb.censer.svc:27017` (Stoat's MongoDB)
   - `AUTUMN_BASE_URL` → `http://autumn.censer.svc:14704` (Stoat file service)
   - `JANUARY_BASE_URL` → `http://january.censer.svc:14705` (Stoat embed service)

### K8s Manifests

Create `dev/k8s/knowledge-browser/` with adapted manifests:
- `postgres.yaml` — KB postgres in `censer` namespace (service name `kb-postgres`)
- `app.yaml` — KB deployment in `censer` namespace with env vars pointing to
  censer infra

### No kind-config.yaml Changes Needed

Tilt uses `kubectl port-forward` for port forwarding — no NodePort or
extraPortMappings required.

### Repo Detection

Same pattern as existing repos (lines 40-54 of Tiltfile):
- Expect KB cloned at `../../knowledge-browser` (sibling to stoat-community)
- `has_kb = os.path.exists(os.path.join(KB_PATH, 'mix.exs'))`
- Clone button if missing

## Future Work

- Discord-Stoat sync service integration
- Multi-tenant configuration across all services
- Unified deployment packaging
