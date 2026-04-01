# ADR-0004: Billing and Payment Infrastructure Licensing

**Status:** Accepted
**Date:** 2026-04-01
**Deciders:** Bryan White

## Context

All Episkopos products are licensed under **AGPL v3-or-later**:
- **Censer** (stoat-backend, stoat-frontend) — chat platform
- **Unveil** (knowledge-browser) — knowledge archive
- **Postern** (discord-stoat-sync) — migration and sync service

We are building a **managed hosting tier** that will charge customers for infrastructure, support, and operational services. This requires payment processing, subscription management, customer portals, and provisioning orchestration.

### The Question

AGPL v3 is a strong copyleft license. Section 13 requires that users interacting with AGPL-covered software over a network must be able to obtain the complete source code, including modifications. Does this mean billing and payment infrastructure must also be open source?

### Design Goals

1. **Keep the core products AGPL** — the community value (sync engine, chat platform, knowledge browser) remains open and protected from proprietary forks
2. **Allow proprietary billing infrastructure** — payment processing, Stripe integration, subscription management, and provisioning tooling can remain private
3. **No license violations** — ensure this separation is compliant with AGPL v3 and does not undermine the copyleft intent
4. **Clear boundaries** — make it obvious to contributors and users where the AGPL boundary lies
5. **Justifiable to the community** — the rationale for this separation should be reasonable and transparent

## Decision

### Architectural Separation via API Boundaries

Billing and payment infrastructure will be built as **separate programs** that communicate with AGPL-covered products exclusively over network APIs (HTTP, gRPC, message queues). This is a well-established pattern under GPL/AGPL interpretation: independent programs that interact only via standard protocols are **not derivative works** and may be licensed independently.

```
┌─────────────────────────────────────┐  ┌────────────────────────────────┐
│  AGPL v3 (Open Source Repos)       │  │  Proprietary (Private Repos)   │
├─────────────────────────────────────┤  ├────────────────────────────────┤
│  stoat-backend (Rust)               │  │  episkopos-billing/            │
│  stoat-frontend (SolidJS)           │  │  ├── Stripe integration        │
│  censer-flutter (Flutter)           │  │  ├── Subscription management   │
│  knowledge-browser (Elixir/Phoenix) │  │  ├── Customer portal           │
│  discord-stoat-sync (TypeScript)    │  │  ├── Provisioning orchestrator │
│  landing site (Astro)               │  │  ├── Admin dashboard           │
│                                     │  │  └── Tenant lifecycle mgmt     │
│            ↑                        │  │              ↑                 │
│            └────── HTTP/gRPC APIs ──┴──┴──────────────┘                │
└─────────────────────────────────────┘                                   
```

### What Can Be Proprietary

The following infrastructure may be kept in private repositories with proprietary licenses:

- **Payment processing** — Stripe SDK integration, webhook handlers, invoicing
- **Subscription management** — plan tiers, usage tracking, billing cycles
- **Customer portal** — account management, payment methods, invoices, billing history
- **Provisioning orchestrator** — spins up tenant instances (Kubernetes operators, instance lifecycle management)
- **Admin tooling** — internal dashboards for managing hosted infrastructure, support tools
- **Infrastructure-as-code** — Terraform modules, Ansible playbooks, Kubernetes manifests for managed infrastructure
- **CI/CD for managed hosting** — pipelines that deploy commercial services (not the open-source products themselves)

### What Must Remain AGPL

The following code is and will always remain AGPL v3:

- **All code in existing open-source repos** — stoat-backend, stoat-frontend, censer-flutter, knowledge-browser, discord-stoat-sync
- **Forks or modifications** of AGPL components (by definition, derivative works)
- **Shared libraries** imported by AGPL code (linking creates a derivative work)
- **Inline billing logic** merged into AGPL codebases (e.g., embedding Stripe calls directly in Stoat's Rust API would make that code AGPL-covered)

### Interface Pattern: License Provider (as seen in ADR-0003)

To maintain a clean boundary, AGPL products define **interfaces** for billing-related queries:

```typescript
// In AGPL repo: defines the contract
interface LicenseProvider {
  canAccessProduct(tenantId: string, product: string): Promise<boolean>;
  getSubscriptionTier(tenantId: string): Promise<'free' | 'paid' | 'enterprise'>;
  getUsageLimits(tenantId: string): Promise<UsageLimits>;
}

// Default implementation (ships with AGPL repo): full access, no gates
class DefaultLicenseProvider implements LicenseProvider {
  async canAccessProduct() { return true; }
  async getSubscriptionTier() { return 'enterprise'; }
  async getUsageLimits() { return UNLIMITED; }
}
```

The **proprietary billing service** provides its own implementation (injected at deployment time) that queries Stripe, checks subscription status, and enforces limits. The AGPL product never sees billing logic — it just calls an interface.

**Rationale:** Self-hosted users get the full product with no artificial restrictions. Managed hosting customers have billing enforced via a separate service that is not part of the AGPL distribution.

### Infrastructure Code

Terraform configurations, Ansible playbooks, Kubernetes manifests, and CI/CD pipelines that **configure and deploy** AGPL software are **not derivative works** of that software. The Free Software Foundation has been clear on this: merely running, installing, or orchestrating GPL/AGPL software does not create copyleft obligations.

Therefore, infrastructure-as-code for managed hosting may remain proprietary. However, any infrastructure code that could benefit the self-hosted community (Helm charts, Docker Compose examples, deployment guides) should ideally be contributed back to the open-source repos.

### Landing Site and Checkout Flow

The landing site (currently in the AGPL-licensed `chat` repo) should **not** embed proprietary JavaScript widgets for checkout inline. Instead, pricing pages should redirect to a separate domain (e.g., `billing.episkopos.community` or `checkout.episkopos.community`) for payment flows. The redirect itself is not a derivative work — it's just a link.

This avoids any ambiguity about whether proprietary code was "distributed" as part of an AGPL-licensed static site.

## AGPL v3 Interpretation

This separation strategy is based on well-established FSF guidance:

### "Mere Aggregation" (GPL FAQ)

The GPL FAQ explicitly addresses this scenario:

> "Where's the line between two separate programs, and one program with two parts? This is a legal question, which ultimately judges will decide. We believe that a proper criterion depends both on the mechanism of communication (exec, pipes, rpc, function calls within a shared address space, etc.) and the semantics of the communication (what kinds of information are exchanged)."

Communication via **standard network protocols** (HTTP REST, gRPC) with **well-defined data exchange** (JSON/protobuf payloads) is consistently recognized as "separate programs," not a combined work.

### Section 13: Remote Network Interaction

AGPL extends GPL by closing the "ASP loophole" — if you modify AGPL software and provide it as a service, users must be able to download your modifications. But this only applies to the **AGPL-covered program itself**, not to every service that program communicates with over a network.

If a proprietary billing service calls Stoat's HTTP API to check if a tenant exists, Stoat is still AGPL, and the billing service is still proprietary. The user accessing Stoat can download Stoat's source — they have no right to download the billing service's source, because the billing service is a separate program with its own license.

### Precedent

This pattern is used throughout the industry:
- **GitLab** — core is MIT-licensed, enterprise billing/features are proprietary
- **Sentry** — core is BSL (source-available), SaaS billing is proprietary
- **WordPress.com** — WordPress core is GPL, Automattic's hosting infrastructure is proprietary

The key is that the **mechanism of interaction** (network APIs) and the **independence of the codebases** (separate repos, no shared runtime) establish them as distinct programs.

## Consequences

### Positive

- **Community trust maintained** — the valuable work (chat, sync, knowledge browsing) remains open and AGPL-protected
- **No license carve-out needed** — unlike brand assets (which required an explicit exception because they're inside AGPL repos), billing code never touches AGPL repos and thus needs no exception
- **Self-hosted users unaffected** — they get the full product with no artificial limits, as intended
- **Clear contributor guidance** — anyone working on the open-source repos knows their work is AGPL; billing work happens in separate private repos
- **Revenue potential unlocked** — we can build a commercial managed hosting business without open-sourcing our entire operational stack

### Negative

- **Perception risk** — some community members may view any proprietary code as "betraying open source" even if legally and ethically sound
- **Boundary maintenance required** — we must be vigilant about not accidentally merging billing logic into AGPL repos
- **Documentation burden** — we need to clearly explain this separation in READMEs, contribution guides, and public communications

### Mitigations

- **Transparent communication** — document this decision publicly (this ADR), explain the rationale, and invite community feedback
- **Generous defaults** — the `DefaultLicenseProvider` gives self-hosted users full access, proving the billing separation is not about crippling the open-source product
- **Contribute infrastructure examples back** — Helm charts, Dockerfiles, deployment guides that help self-hosters should live in the AGPL repos
- **Code review discipline** — billing-related PRs must never land in open-source repos; enforce this in CI and through maintainer guidelines

### Risks

- **License interpretation challenges** — while FSF guidance supports this pattern, a determined legal challenger could argue the services are too tightly integrated to be "separate programs"
- **Community backlash** — transparency and generous defaults should mitigate this, but some friction is inevitable
- **Accidental leakage** — a developer might accidentally commit billing code to an open-source repo; robust CI checks and `.gitignore` rules help prevent this

## Related Decisions

- **ADR-0003: Postern Multi-Tenant Architecture** — describes the `LicenseProvider` pattern and open-core billing model for Postern specifically
- **BRANDING.md** — documents the trademark carve-out (brand assets are not AGPL-licensed, even though they're in AGPL repos)
- **AGPL v3 license files** — all product repos include `LICENSE` and `NOTICE` files clarifying AGPL terms

## References

- [GNU AGPL v3 Full Text](https://www.gnu.org/licenses/agpl-3.0.html)
- [GPL FAQ: Combining GPL and Non-GPL Software](https://www.gnu.org/licenses/gpl-faq.html#MereAggregation)
- [FSF: What is Copyleft?](https://www.gnu.org/licenses/copyleft.html)
- Open-core precedents: GitLab, Sentry, Mattermost, Grafana
