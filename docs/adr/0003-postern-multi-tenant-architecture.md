# ADR-0003: Postern Multi-Tenant Architecture

**Status:** Accepted
**Date:** 2026-03-23
**Deciders:** Bryan White

## Context

The discord-stoat-sync project currently operates as a single-tenant tool: one deployment serves one community. We want to evolve it into **Postern** — a multi-tenant, hosted migration and sync service that community managers can use self-service.

### Goals

1. **Minimize user effort** — community managers should be able to onboard with minimal steps
2. **Multi-tenancy** — one Postern deployment serves many communities
3. **Revenue** — charge for the service to cover infrastructure costs
4. **Integrate with the Episkopos product suite** — Censer (chat) and Unveil (knowledge browser)

### Current State

- Next.js app with Prisma ORM
- Syncs Discord → Stoat using a manually-configured bot token
- Single-tenant: deployed once per community
- No web UI for configuration (CLI/config-driven)

## Decision

### Authentication: Per-Tenant Bot Model

**Discord OAuth2** handles user identity:
- Community manager signs in with Discord
- We enumerate their servers via the `guilds` scope
- They select which server to migrate/sync

**Per-tenant Discord bot** handles data access:
- Each community manager creates their **own** Discord bot application
- Postern provides a streamlined, guided setup wizard that walks them through:
  1. Creating a bot at Discord Developer Portal (with direct link)
  2. Configuring the required intents (Message Content, Server Members)
  3. Generating and pasting the bot token (once)
  4. Inviting their bot to their server (pre-built invite URL with correct permissions)
- The bot token is stored encrypted, per-tenant — compromise of one tenant's bot does not affect others
- Each tenant's bot has independent Discord API rate limits

**Rationale for per-tenant bots over a single managed bot:**
- **Sovereignty:** Community managers own and control their bot — they can revoke it, audit its permissions, and manage it independently. This aligns with Postern's core value proposition: helping communities take ownership of their platform.
- **Liability:** Episkopos does not hold privileged access to every tenant's Discord server. Each community is responsible for their own bot's permissions and lifecycle.
- **Scalability:** Discord limits bots to 100 servers without verification. A single managed bot would hit this limit quickly, requiring Discord's verification process and creating a dependency on Discord's approval.
- **No future migration:** Starting with per-tenant bots avoids ever needing to ask existing community managers to create their own bots later — a disruptive migration that would erode trust.
- **Isolation:** A security incident affecting one tenant's bot token does not cascade to other tenants.

**Censer/Stoat destination auth** is tiered:
- **Censer instances** (our Stoat fork): OAuth provider support is planned but not yet implemented in Stoat upstream. Once available, Censer will support OAuth-based server enumeration and permission checking.
- **Generic Stoat instances** (third-party): API key/bot token only. No OAuth provider exists in upstream Stoat, so users must manually provide credentials. This is acceptable — these are technically sophisticated users running their own Stoat instances.
- **Future**: When Censer OAuth is implemented, the flow becomes: Discord OAuth login → pick source server → Censer OAuth → pick destination server → configure sync → go.

### User Flow (Target State)

1. Visit Postern web UI
2. "Sign in with Discord" (OAuth2)
3. See list of Discord servers they admin
4. Select server to migrate/sync
5. Guided Discord bot setup:
   a. Link to create bot at Discord Developer Portal
   b. Checklist: enable Message Content intent, Server Members intent
   c. Paste bot token (stored encrypted)
   d. One-click: "Invite your bot to [server name]" (pre-built URL with required permissions)
   e. Postern verifies bot is in the server and has correct permissions
6. Connect destination:
   - Censer: OAuth flow (when available) or API key
   - Generic Stoat: API key / bot token
7. Configure sync (channels, roles, history depth, continuous sync vs. one-shot migration)
8. Dashboard shows sync status, history, errors

### Multi-Tenancy Model

- Each community manager gets an **account** (Discord identity)
- Each account can manage multiple **sync configurations** (source server → destination instance)
- Tenant isolation via Prisma row-level scoping (tenant_id on all models)
- Shared infrastructure, per-tenant billing

### Revenue Model

- Free tier: one-shot migration up to N messages / N channels
- Paid tier: continuous sync, higher limits, priority support
- Billing integration TBD (Stripe likely)

### Postern as Management Hub

Postern serves as the **unified management interface** for communities that migrated from Discord. Beyond sync, it provides dashboard panels for managing the tenant's connected Censer instance and Unveil instance — all from the same authenticated session.

This is a natural extension of Postern's role: communities escape Discord *through* Postern, and once through, they manage their sovereign stack from the same place. The `stoatFlavor` field on each tenant gates which management panels are visible:

- **Standalone** (BYOS / generic Stoat): sync dashboard only
- **Canonical** (self-hosted Censer): sync + Censer management
- **Hosted** (Episkopos-managed Censer): sync + Censer management + Unveil management

Dashboard modules are organized under tenant-scoped routes (`/dashboard/[tenantSlug]/censer/`, `/dashboard/[tenantSlug]/unveil/`) with clean boundaries, so they could be extracted into a separate app if the monolith ever needs splitting.

### Scope Boundary: Fresh Censer Users

Postern is **not** a universal portal for all Censer users. Communities that start fresh on Censer (no Discord migration) use Censer's native admin panel for management. Postern's management features are exclusively for tenants created through Postern's onboarding flow.

This keeps Postern's scope honest — it is the escape hatch from centralized platforms, not a general-purpose admin console.

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                      Postern Web UI                       │
│                    (Next.js frontend)                     │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ Discord  │  Sync    │ Censer   │ Unveil   │  Billing     │
│ OAuth +  │  Dash &  │ Mgmt     │ Mgmt     │  Management  │
│ Server   │  Config  │ (gated)  │ (gated)  │  (future)    │
│ Picker   │          │          │          │              │
├──────────┴──────────┴──────────┴──────────┴──────────────┤
│                       Postern API                         │
│                  (Next.js API routes)                     │
├──────────┬──────────┬──────────┬─────────────────────────┤
│ Auth     │  Sync    │  Tenant  │  Product Management     │
│ Service  │  Engine  │  Mgmt    │  (Censer + Unveil APIs) │
├──────────┴──────────┴──────────┴─────────────────────────┤
│                  Prisma + PostgreSQL                      │
│              (multi-tenant, row-scoped)                   │
├──────────┬──────────────────┬────────────────────────────┤
│ Discord  │  Censer/Stoat    │  Unveil                    │
│ Bot API  │  APIs (dest +    │  API                       │
│          │  management)     │  (knowledge browser)       │
└──────────┴──────────────────┴────────────────────────────┘

Visibility of Censer/Unveil management panels is gated by stoatFlavor:
  standalone → sync only | canonical → + Censer | hosted → + Censer + Unveil
```

## Consequences

### Positive
- Community sovereignty: each tenant owns and controls their own Discord bot
- No single point of trust — Episkopos never holds privileged access to tenant servers
- Independent rate limits per bot — no shared throttling
- No 100-server ceiling or Discord verification dependency
- Revenue potential from hosted service
- Reusable OAuth infrastructure for Censer integration later
- Single auth flow: community managers sign in once (Discord OAuth) and manage sync, Censer, and Unveil from one dashboard
- Progressive disclosure via stoatFlavor — standalone users see a focused sync tool; full suite users see everything

### Negative
- Slightly more onboarding friction than a managed bot (user must create a bot at Discord Developer Portal)
- Multi-tenancy adds complexity (tenant isolation, billing, abuse prevention)
- Censer OAuth dependency means full flow isn't possible until Stoat fork adds OAuth provider support

### Mitigations
- Guided wizard with step-by-step instructions, direct links, and permission verification reduces bot setup friction
- UX copy emphasizes sovereignty rationale so the extra step feels motivated, not arbitrary

### Risks
- Bot permission model may change with Discord policy updates (the very thing driving our audience to us)
- Stoat/Censer API stability — we're building on a fork of a fork

## Related Decisions

- [Upstream Git Workflow](../../) — how we manage stoat-frontend/backend forks
- Episkopos branding — Censer (chat), Unveil (knowledge browser), Postern (migration)
- Censer OAuth provider — prerequisite for full Censer integration (tracked separately)
- Postern as management hub — Postern manages the full stack for migrated communities; fresh Censer users use native admin
