# Feature — REQ-nnn — <Short title>

| | |
|---|---|
| **ID** | REQ-nnn |
| **PRD** | [prd.md](prd.md) |
| **Technical plan** | [technical-plan.md](technical-plan.md) |
| **Test plan** | [test-plan.md](test-plan.md) |
| **Owner (code)** | Team / person |
| **Shipped in** | PR #…, release/tag, date |
| **Status** | In development / Live / Deprecated |

## 1. Summary

Two sentences: what it does and for whom. Written for someone who has never
seen the PRD.

## 2. How it works

The design **as built**. Main components and how a request/data flows
between them. A diagram if more than three moving parts.

```
[client] ─▶ [api: POST /exports] ─▶ [ExportService] ─▶ [LedgerClient] ─▶ ledger
                                        │
                                        └─▶ [exports table]
```

Key files / modules:

| Path | Responsibility |
|------|----------------|
| | |

## 3. Interfaces

Endpoints, events, CLI commands, UI entry points — with shapes or links to
the API reference.

## 4. Data

Tables / fields written and read, migrations applied, retention.

## 5. Configuration

| Key / flag / env var | Default | Effect | Read in |
|----------------------|---------|--------|---------|
| | | | |

## 6. Operations

- **Healthy looks like:** …
- **Logs to look for:** (logger name, message pattern, includes `REQ-nnn` or feature tag)
- **Metrics / alerts / dashboard:** links
- **Common failures and what to do:**

| Symptom | Likely cause | Action |
|---------|-------------|--------|
| | | |

## 7. Testing

How to run the tests for this feature locally; fixtures and where they come
from; any manual steps.

```bash
<command>
```

## 8. Dependencies

New libraries or services introduced and why they were chosen.

## 9. Decisions

Short list of design decisions with one-line rationale; link ADRs for the
ones that outlive this feature.

- …

## 10. Known limitations and deferred scope

| Limitation / deferred item | Reason | Follow-up (REQ / OQ) |
|----------------------------|--------|----------------------|
| | | |

## 11. Lessons (post-release)

Anything that surprised the team in production or during rollout.

## 12. Change log

| Date | PR | Change |
|------|----|--------|
| | | Initial |
