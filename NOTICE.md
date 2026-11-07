# Notice

## Licence summary (read first)

- **Web UI: QuantDinger Frontend Source-Available License v1.0.** Copyright (c) 2026 Open Byte Inc. This covers the image `ghcr.io/openbyteinc/quantdinger-frontend` and its source, https://github.com/OpenByteInc/QuantDinger-Vue (`LICENSE`). The H5 mobile client (https://github.com/OpenByteInc/QuantDinger-Mobile, not deployed by this template) is under the same licence.
  - Use is free only for non-commercial purposes, or for qualified non-profit entities.
  - Commercial use of any kind needs a separate commercial licence from Open Byte Inc. (support@quantdinger.com). The licence counts as commercial any use intended for, or resulting in, commercial advantage or revenue, including services based on the software.
  - The licence is revocable. It forbids sublicensing.
  - Copyright notices and all "Powered by QuantDinger" branding, watermarks and attribution must stay in place.
- **Backend, workers, migrations and MCP server: Apache License 2.0.** Copyright 2025-2026 Open Byte Inc. and QuantDinger contributors (`REUSE.toml`, `LICENSE`, `LICENSES/Apache-2.0.txt`). Source: https://github.com/OpenByteInc/QuantDinger
- **Trademarks.** "QuantDinger", its logo and brand assets belong to Open Byte Inc. and are governed by `TRADEMARKS.md`, not by the code licences. This template uses the name only to identify the unmodified software it deploys. It does not use the logo; the listing icon is a neutral Lucide icon.
- This is a **community template, not affiliated with or endorsed by Open Byte Inc.** It is not legal advice. Anyone who deploys it is responsible for complying with these licences, with exchange and broker terms, and with the law where they operate.

## What this repository contains

Railway configuration, three Dockerfiles and three small scripts written for this template:

| File | What it does |
|---|---|
| `services/backend/Dockerfile`, `railway_quantdinger.py` | Builds from the published backend image (unchanged) and adds the start/pre-deploy wrapper: env-file preparation, secret checks, schema wait, thread caps. It then hands over to upstream's own `docker-entrypoint.sh`. |
| `services/web/Dockerfile`, `05-railway-nginx.sh` | Builds from the published web UI image **unmodified** and adds one nginx entrypoint hook. At container start, the hook replaces the Docker-only `resolver 127.0.0.11` line of the nginx config template with the container's DNS server and trusts `X-Forwarded-For` from private addresses. The web application, its files and its branding are not changed. |
| `services/mcp/Dockerfile`, `railway_mcp.py`, `requirements.txt` | Installs the MCP server's Python files, downloaded at build time from the v5.8.4 commit and checked by SHA-256 (not stored here), plus their PyPI dependencies pinned by hash. The wrapper serves a placeholder until an Agent Token is configured. |

No upstream source file is copied into this repository or modified.

## Software deployed

| Software | Licence | Used as |
|---|---|---|
| QuantDinger backend v5.8.4 | Apache-2.0 | `ghcr.io/openbyteinc/quantdinger-backend:v5.8.4@sha256:3878e94a1344a979e98b689369ed3fafe51ed065c3d51b11782b7f3dd52d4e26`. The image label revision is `be718de0034acea548033aa1627529ac62ed0dda` (tag v5.8.4). Its `/app` layer was compared with the tag source and is identical. |
| QuantDinger web UI 5.8.4 | QuantDinger Frontend Source-Available License v1.0 | `ghcr.io/openbyteinc/quantdinger-frontend:5.8.4@sha256:fc993eb1eef5152097e95db8969691692b7c02272055fc801e2c603761c09b8d`, built from QuantDinger-Vue `97ec75570d4c500be8abf209c493040b6a07274b`. The licence file is identical there and on `main` (blob `71c452c6`). |
| QuantDinger MCP server (`quantdinger_mcp`, package version 0.6.2 as in the v5.8.4 source) | Apache-2.0 (`mcp_server/LICENSE`) | Files from https://raw.githubusercontent.com/OpenByteInc/QuantDinger/be718de0034acea548033aa1627529ac62ed0dda/mcp_server/, SHA-256-checked at build. The PyPI wheel 0.6.2 is older than this source and is not used. |
| MCP Python dependencies (`mcp` 1.28.1, `httpx` 0.28.1, `pydantic`, `starlette`, `uvicorn`, …) | MIT / BSD / Apache-2.0 (per package) | From PyPI, pinned with hashes in `services/mcp/requirements.txt` |
| Python 3.12.15 base image | PSF and Debian package licences | `python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70` (the base upstream's MCP Dockerfile pins) |
| Apache Kafka 4.3.1 | Apache-2.0 | `apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837` (upstream compose default) |
| PostgreSQL 18 | PostgreSQL License | `ghcr.io/railwayapp-templates/postgres-ssl:18` (Railway's base image) |
| Redis 8.2 | RSALv2 / SSPLv1 / AGPLv3 (Redis 8 tri-licence) | `redis:8.2` (Railway's base Redis service), two instances |
| Lucide icons, Simple Icons (Kafka) | ISC / CC0 | Referenced by URL from jsDelivr, not copied |

Third-party components inside the QuantDinger images carry their own licences (Python packages in `requirements.lock`, the nginx/Alpine base of the web UI, npm packages compiled into the web UI).

## Third-party services the software can call

Exchanges and brokers, market-data APIs (Binance public data, Finnhub, Twelve Data, AkShare sources, FRED, SEC EDGAR, and others), LLM providers (OpenRouter, OpenAI, Google, DeepSeek, xAI, MiniMax, or any OpenAI-compatible endpoint) and the optional JEV pre-trade filter (`api.typesafe.ai`, used only when `JEV_API_KEY` is set). Each has its own terms. LLM calls via OpenRouter send `HTTP-Referer: https://quantdinger.com` (upstream code). No telemetry endpoint was found in the backend code. The web UI bundle was not audited for analytics.

## Verified against

| What | Upstream file | Ref | Checked |
|---|---|---|---|
| Release, tag, image tags | GitHub release v5.8.4 (2026-11-06T18:09Z), `CHANGELOG.md`, ghcr tag lists | `be718de0` | 2026-11-07 |
| Services, commands, Redis tiers, Kafka settings, pools | `docker-compose.yml`, `docker-compose.ghcr.yml`, `docker-compose.production.yml`, `.env.example`, `backend_api_python/env.example` | `be718de0` | 2026-11-07 |
| Entrypoint, env-file handling, Settings writes | `backend_api_python/docker-entrypoint.sh`, `run.py`, `app/__init__.py`, `app/services/settings/{env_file,runtime,capabilities}.py`, `app/routes/settings.py` | `be718de0` | 2026-11-07 |
| Migrations and ledger | `app/commands/migrate.py`, `app/utils/db.py`, `migrations/` | `be718de0` | 2026-11-07 |
| Admin bootstrap, registration, live-trading gates, client IP | `app/services/user_service.py`, `app/routes/auth.py`, `app/routes/strategy.py`, `app/services/strategy_v2/deployment.py`, `app/routes/quick_trade.py`, `app/services/auth_session.py` | `be718de0` | 2026-11-07 |
| Health, workers, Kafka topics, Celery | `app/openapi/routes/health.py`, `app/commands/{worker_health,kafka_topics}.py`, `app/events/{topics,kafka}.py`, `app/celery_app.py`, `app/config/redis_urls.py`, `gunicorn_config.py` | `be718de0` | 2026-11-07 |
| MCP server | `mcp_server/{README.md,Dockerfile,pyproject.toml}`, `src/quantdinger_mcp/server.py`; MCP SDK 1.28.1 `mcp/server/fastmcp/server.py`, `mcp/server/auth/routes.py` | `be718de0`; PyPI `mcp` 1.28.1 | 2026-11-07 |
| Web UI nginx template | `/etc/nginx/templates/default.conf.template` from the frontend image layer `sha256:7cd6305c…` | image 5.8.4 | 2026-11-07 |
| Kafka image start scripts | `/etc/kafka/docker/{run,configure,launch,server.properties}` from the `apache/kafka:4.3.1` layers | 4.3.1 | 2026-11-07 |
| Licences and policy | `LICENSE`, `REUSE.toml`, `TRADEMARKS.md`, `docs/compliance/README.md`, README "License and commercial terms"; QuantDinger-Vue and QuantDinger-Mobile `LICENSE` | `be718de0`; Vue `97ec7557` and `main`; Mobile `master` | 2026-11-07 |
