# Hosting the query service (T-126)

Status: **proposal, for the owner to decide** (D-14: a hosted server is the owner's call). Raised 16 Nov 2026.

## Why

The project's aim is a parcel fact service that AI agents can query. Today the service (`service/`) runs only on a
machine that holds the data, so nobody outside can use it. The national index covers every parcel in New Zealand and
rebuilds itself monthly (D-27), so it is the right thing to put online first.

## What is ready

- **The service over HTTP.** `LANDQ_TRANSPORT=http python3 service/server.py` serves the same tools (`about`, `columns`,
  `parcel`, `search`) as MCP over HTTP at `/mcp`, stateless, with a limit of 60 requests a minute per address, a 64 KB
  cap on each request, a check that requests name this host (against DNS rebinding) and `/health` for the host's
  checks. Tested: a parcel lookup over HTTP, the limit, the host check (`service/test_service.py`).
- **A container.** `service/host/Dockerfile` with `service/host/start.py`: at start it fetches the newest published
  national index (a public GitHub release, no key), prepares it (`prepare_national.py`, about 15 s) and serves it. A
  restart reuses the prepared copy. It needs about 1 GB of memory (DuckDB is capped at 1 GB); the prepared index is
  about 240 MB.
- **Speed.** On the national data a parcel lookup takes about 0.1 s and an area search about 0.15 s; a query is stopped
  after 10 s.

## Before it goes public

1. The first national index is published as a release, after review 27 (T-102). The container serves releases only.
2. The fresh-eyes review of the service (running, 16 Nov) finds nothing serious, or its findings are fixed.
3. The owner chooses a host below and creates the account; secrets stay in the host's settings, never in chat.

## Options

Prices are monthly, checked 16 Nov 2026 from the providers' pages and price trackers; confirm on the provider's own
page before signing up.

| Option | Cost | Work for the owner | Notes |
| --- | --- | --- | --- |
| **A. Fly.io**, one shared-CPU machine with 1 GB, always on | about US$7 | an account and a card; then `fly launch` from the repository | HTTPS and a `*.fly.dev` name included; simplest |
| **B. Cloudflare Containers**, on the Workers Paid plan | US$5 plan, plus about US$6 of memory if always on (it includes 25 GB-hours a month), or less if it sleeps when idle | the existing Cloudflare account (R2 is there already); the US$5 plan | one bill with R2; a sleeping container has to prepare the index again on waking (about a minute) unless it keeps a disk |
| **C. Hetzner Cloud**, smallest shared server | about €5 | an account; and someone to keep the server patched | cheapest, but HTTPS, updates and restarts are ours to look after |

**Recommendation: A**, about US$7 a month, inside the US$20 monthly budget (D-14). It runs the tested service unchanged,
needs no server care, and can be moved to B later if one bill with R2 matters more. B is a close second because the
Cloudflare account exists already.

## What it does not do yet

- No sign-in or keys: anyone may query, limited per address. Paid access, if wanted, is a later decision.
- Council results (Kāpiti, Porirua) are not served by this container; they can be added as a second instance.
- The parcel report (1 m analysis on demand) stays on GitHub (`report.yml`); serving it on request would need more CPU.
