# Stoat Community

Welcome to the central hub for the **Episkopos** community's **Stoat** fork(s).

This repository is the source of truth for:
- 🐛 **Bug Reports**
- 💡 **Feature Requests**
- 🎨 **UX Feedback**
- 🔒 **Security Reports**

## Service Status

Check real-time service health at **[status.episkopos.community](https://status.episkopos.community)**.

## Where To File Issues
Use **GitHub Issues** in this repository.

1. [Open `New issue`](https://github.com/Episk-pos/stoat-community/issues/new/choose)
2. Choose a template
3. Fill all required sections

Available templates:
- `Bug Report`
- `Feature Request`
- `UX Feedback`
- `Security Issue`

## Before Opening A New Issue
1. Search existing issues to avoid duplicates.
2. Confirm behavior on the latest available Stoat build.
3. Collect evidence:
   - Reproduction steps
   - Screenshots or video
   - Environment details (OS, client, version)
   - Logs or error messages

## Bug Reports
Good bug reports include:

1. Clear summary of the problem
2. Exact reproduction steps
3. Expected vs actual behavior
4. Frequency, severity, and workaround
5. Environment + evidence

Use the `Bug Report` template.

## Feature Requests
Strong feature requests include:

1. User problem being solved
2. Desired outcome
3. Proposed solution
4. Alternatives considered
5. Scope and impact
6. Acceptance criteria

Use the `Feature Request` template.

## UX Feedback
Use `UX Feedback` when reporting friction, confusion, or usability issues that may not be strict bugs.

Helpful UX submissions include:
- Current experience and pain points
- Suggested improvement
- Why it matters to users
- Supporting examples and references

## Security Reports
Use `Security Issue` for vulnerabilities.

If the report includes sensitive exploit details, do not post proof-of-concept details publicly. Provide impact and reproduction at a safe level so maintainers can coordinate remediation.

## Triage Flow
Maintainers will generally:

1. Validate scope and request missing information
2. Apply labels (`type`, `priority`, `severity`, `area`, `status`)
3. Deduplicate and link related issues
4. Move accepted issues into planning/in progress

Higher-quality issue submissions reduce triage turnaround time.

## Dev Stack

A full local development environment using **Tilt** + **Kind** lives in [`dev/`](dev/). It runs the entire Stoat backend (Delta, Bonfire, Autumn, January) and infrastructure (MongoDB, Redis, MinIO, RabbitMQ, Maildev) in a local Kubernetes cluster, with the frontend Vite dev server running natively for fast HMR.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Kind](https://kind.sigs.k8s.io/)
- [Tilt](https://docs.tilt.dev/install.html)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Rust / Cargo](https://rustup.rs/)
- [pnpm](https://pnpm.io/installation)
- [just](https://github.com/casey/just)

### Quick Start

```bash
cd dev/

# Check prerequisites and create the Kind cluster
just setup

# Start everything (Tilt UI opens in your browser)
just up
```

If `stoat-backend` or `stoat-frontend` aren't cloned as sibling directories, the Tilt UI will show clone buttons to set them up automatically.

### Commands

| Command | Description |
|---------|-------------|
| `just setup` | Check prerequisites, create Kind cluster |
| `just up` | Start the full dev stack via Tilt |
| `just down` | Stop Tilt (cluster stays intact) |
| `just test` | Run frontend E2E tests against the stack |
| `just status` | Show cluster, pods, and Tilt resources |
| `just logs <service>` | Tail logs for a service (e.g., `delta`, `bonfire`) |
| `just nuke` | Delete the Kind cluster entirely |

### Ports

All services use the `14xxx` range to avoid conflicts with other dev stacks (Fray.run, execos, etc.) that may run concurrently.

| Port | Service |
|------|---------|
| 5173 | Frontend (Vite dev server, local) |
| 14702 | Delta (API) |
| 14703 | Bonfire (WebSocket) |
| 14704 | Autumn (file server) |
| 14705 | January (embed proxy) |
| 14717 | MongoDB (debug) |
| 14672 | RabbitMQ management UI (debug) |
| 14080 | Maildev web UI (debug) |
| 14009 | MinIO API (debug) |

### Architecture

```
┌─────────────────────────────────────────────────┐
│  Host                                           │
│  ┌───────────────┐                              │
│  │ Vite dev :5173│ ◄── browser                  │
│  └───────────────┘                              │
│                                                 │
│  ┌─ Kind cluster (kind-stoat) ────────────────┐ │
│  │  namespace: stoat                          │ │
│  │                                            │ │
│  │  delta:14702  bonfire:14703                 │ │
│  │  autumn:14704  january:14705               │ │
│  │                                            │ │
│  │  redis  mongodb  minio  rabbitmq  maildev  │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

Backend binaries are built on the host with `cargo build --release`, then packaged into thin `debian:12-slim` Docker images and loaded into Kind. This avoids slow in-container Rust compilation.
