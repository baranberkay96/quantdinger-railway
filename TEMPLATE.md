# QuantDinger v5 AI Trading Research and Backtesting — Railway template spec

## Listing

| Field | Value |
|---|---|
| Name | **QuantDinger v5 AI Trading Research and Backtesting** (`v5` = major of the pinned release v5.8.4) |
| Description | AI quant research, Python strategies, backtesting and paper trading (67 chars) |
| Category | AI/ML |
| Tags | quantdinger, quant, trading, backtesting, algorithmic-trading, ai-agents, mcp, kafka, celery |
| Icon | `https://cdn.jsdelivr.net/npm/lucide-static@1.59.0/icons/chart-candlestick.svg` (neutral Lucide icon, ISC; **not** the QuantDinger logo, see `TRADEMARKS.md`) |
| Repo | `baranberkay96/quantdinger-railway`, services in `/services/<svc>` |
| User input at deploy | **None required.** All secrets and the admin password are generated. Optional: AI provider keys, `ADMIN_EMAIL`, and the MCP Agent Token (issued after login). |

## Licence decision (read before publishing)

The web UI image is under Open Byte Inc.'s **QuantDinger Frontend Source-Available License v1.0**. It is free only for non-commercial use, revocable, and requires "Powered by QuantDinger" branding to stay. The backend, workers and MCP server are Apache-2.0. A kickback-earning marketplace template plausibly counts as commercial use of the web UI. The user was told this (report `_reports/round9/94-quantdinger.md`) and decided to publish anyway, as with Multica.

The package therefore:
- states the licence split near the top of README and NOTICE, with the commercial-licence contact (support@quantdinger.com);
- says it is a community template, not affiliated, and gives no legal advice;
- uses the frontend image unmodified, with no branding changes (one nginx entrypoint hook rewrites only the DNS resolver line of the nginx config);
- uses a neutral icon.

## Base market templates

None. No QuantDinger template exists on Railway (`_market/` is empty; confirmed in the task). Upstream ships `backend_api_python/railway.json` and `mcp_server/railway.json` for single-service Dockerfile deploys only: a backend with no workers, Kafka or Redis tiers. They were read but not used. The package is built from upstream's `docker-compose.yml` / `docker-compose.ghcr.yml` / `docker-compose.production.yml` at v5.8.4 and the published images.

## Pinned versions

| Service(s) | Source | Version | Built / released | Checked |
|---|---|---|---|---|
| Backend + 8 workers | `ghcr.io/openbyteinc/quantdinger-backend:v5.8.4@sha256:3878e94a…d4e26` (index; amd64 `sha256:8806b6c8…62bbb28`; `5.8.4` = same digest) via `services/backend` | v5.8.4 (`be718de0`) | 2026-11-06 18:11 UTC | 2026-11-07 |
| Web | `ghcr.io/openbyteinc/quantdinger-frontend:5.8.4@sha256:fc993eb1…09b8d` (amd64 `sha256:70d3fa4d…5d0e394`) via `services/web` | 5.8.4 (QuantDinger-Vue `97ec7557`) | 2026-11-04 | 2026-11-07 |
| MCP Server | `python:3.12-slim-bookworm@sha256:6a0e06f5…bc70` (Python 3.12.15) + `mcp_server/` files at `be718de0` (SHA-256 checked) + PyPI deps by hash (`mcp` 1.28.1) | quantdinger_mcp 0.6.2 (v5.8.4 source) | — | 2026-11-07 |
| Kafka | `apache/kafka:4.3.1@sha256:77e3df90…32837` | 4.3.1 (upstream default) | 2026-06-17 | 2026-11-07 |
| Postgres | `ghcr.io/railwayapp-templates/postgres-ssl:18` (Railway base; index `sha256:4fc833b4…7c863`) | PostgreSQL 18 | — | 2026-11-07 |
| Redis, Redis Jobs | `redis:8.2` (Railway base; index `sha256:b0b01167…accc8d`) | 8.2 | — | 2026-11-07 |

- The QuantDinger-Vue frontend has its own release line: it had published 5.8.5–5.8.10 by 2026-11-06. Upstream compose moves both sides with one `IMAGE_TAG`, so the web UI stays on `5.8.4`, the release paired with the backend.
- Upstream's `VERSION` file still says 5.6.1 at v5.8.4. The image labels (`org.opencontainers.image.version=5.8.4`, revision `be718de0`) and the release are authoritative.
- The `/app` layer of the backend image (app code, `env.example`, migrations) and its `docker-entrypoint.sh` are byte-identical to the tag source (diffed).

## Architecture

```
Internet ─HTTPS─▶ Web (nginx, SPA)  ── /api/* ──▶ Backend (gunicorn [::]:5000)            public :80
Internet ─HTTPS─▶ MCP Server (/mcp, static bearer) ──▶ Backend /api/agent/v1 (Agent Token)  public :7800
Backend ── pre-deploy: python -m app.commands.migrate (ledger qd_bootstrap_migrations)
Backend, workers ──▶ Postgres (all state) · Redis (cache, LRU) · Redis Jobs (Celery broker/results, AOF, noeviction)
Trading Worker ─ strategy runtimes, orders, position sync ─▶ exchanges (only with user-saved keys)
Scheduler ─ market data, portfolio monitor            Celery Beat ─▶ Redis Jobs ─▶ Celery Worker (ai, maintenance)
                                                                              └─▶ Celery Backtest Worker (backtest)
API / Trading ─ events ─▶ Kafka (KRaft, [::]:9092) ─▶ Strategy Dispatcher ─▶ Strategy Evaluator ; Kafka Audit Worker
Dispatcher/Evaluator/Audit pre-deploy: python -m app.commands.kafka_topics (idempotent)
```

## Design decisions (verified in the v5.8.4 sources and image layers)

### Service mapping

| Upstream compose service | Railway |
|---|---|
| postgres, redis, redis-jobs, kafka | Postgres, Redis, Redis Jobs, Kafka |
| migration (one-shot) | Backend **pre-deploy** `railway-quantdinger migrate` (lesson 6), 60×10 s retries |
| kafka-init (one-shot) | **pre-deploy** `railway-quantdinger kafka-topics` on the three Kafka consumers (idempotent, `TOPIC_ALREADY_EXISTS` is fine) |
| backend, trading-worker, kafka-audit-worker, strategy-dispatcher-worker, strategy-evaluator-worker, scheduler-worker, celery-worker, celery-backtest-worker, celery-beat | Backend + 8 worker services, one image, one start command each |
| frontend | Web |
| mcp (compose profile) | MCP Server |
| env-sync (one-shot) | not needed; the wrapper does the same merge into the env file |
| mobile (H5) | **left out**: a second public UI under the same source-available licence; can be added as an image service with `BACKEND_URL` |
| observability overlay (Prometheus/Grafana/Alertmanager) | **left out**; README points to `docker-compose.observability.yml` |

### One backend image, a wrapper, upstream's entrypoint

- **Thin build, not an image service.** `services/backend/Dockerfile` is `FROM` the pinned image plus `railway_quantdinger.py`. The wrapper needs to run before upstream's entrypoint. All nine services share `rootDirectory /services/backend`, and `QUANTDINGER_BACKEND_IMAGE` on Backend is the build argument the workers reference, so they cannot drift. `ENTRYPOINT []` + an explicit start command makes the result independent of whether Railway's start command replaces ENTRYPOINT or CMD. The build runs `railway-quantdinger --self-test` (entrypoint, `env.example`, migration files, psycopg2, command modules present).
- **The `.env` problem.** Without the compose bind mount, upstream's `docker-entrypoint.sh` copies `/app/env.example` to `/app/.env`, and every process loads it (`load_dotenv(override=False)`). Unset variables therefore fall back to example values: `ADMIN_PASSWORD=123456`, `REDIS_HOST=redis`, `CELERY_REDIS_HOST=redis-jobs`, `KAFKA_BOOTSTRAP_SERVERS=localhost:29092`, `ENABLE_REGISTRATION=true`, `LIVE_TRADING_ENABLED=true`. Worse, after a Settings save the API runs `load_dotenv(override=True)` (`app/services/settings/runtime.py`), and the UI's feature flags (`/api/settings/public-config`, `get_feature_flags(read_env_file())`) come **from the file, not the environment**. The wrapper therefore:
  1. creates the file from `env.example` if missing, and appends keys that a newer `env.example` adds (what upstream's env-sync does);
  2. writes every non-empty Railway variable whose key is in the file into it (quoting identical to upstream's `_format_env_line`). The file then always shows and reloads the real values, and Railway variables win at every start;
  3. always writes the UI feature flags (`ENABLE_REGISTRATION`, `LIVE_TRADING_ENABLED`, `AGENT_LIVE_TRADING_ENABLED`, `BROKER_ACCOUNTS_ENABLED`, `AGENT_GATEWAY_ENABLED`, `BILLING_ENABLED`, `MARKETPLACE_ENABLED`);
  4. removes **empty** Railway variables whose key is in the file, so a key saved on the Settings page applies after a restart. `ADMIN_PASSWORD` and the secrets are never dropped.
  - Backend keeps the file on its volume (`QUANTDINGER_ENV_FILE=/app/data/.env`, `/app/.env` symlinked to it), so Settings-page values persist. Workers get a fresh file each start.
  - Every connection, secret, process and feature variable is also set explicitly as a Railway variable on all nine services. The only values left to upstream's `env.example` are tuning knobs: the same file upstream's installer uses.
- **Secrets fail closed** (lesson 29). `SECRET_KEY` and `CREDENTIAL_ENCRYPTION_KEY` must be 32+ characters, or the process refuses to start. The upstream entrypoint would otherwise invent a random key per container, breaking sessions and stored exchange credentials across services. On the API, `ADMIN_PASSWORD` must be 8–72 bytes and not `123456`. An invalid `ADMIN_USER` falls back to `admin` with a warning.
- **Schema wait.** Workers wait (up to `QD_SCHEMA_WAIT_SECONDS`=900, then start anyway) until the `qd_bootstrap_migrations` rows `schema-init` and `strategy-v2-templates` carry the SHA-256 of this image's `init.sql` / `strategy_v2_templates.sql`. That is the first and last component that `app.utils.db._apply_init_sql` records. Compose expresses the same dependency with `depends_on: migration`.
- **Pre-deploy migration** runs `python -m app.commands.migrate` with `SKIP_AUTO_MIGRATE=false` forced. `init_database` honours that flag even in the migration command, and all services set it to `true`. The components are checksummed and idempotent; a redeploy logs `unchanged, skipped`.
- **Thread caps** (lesson 15): `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and `NUMEXPR_MAX_THREADS` are set from the cgroup CPU quota, capped at `QD_THREAD_CAP`=4, unless set explicitly.
- **Dual-stack API.** `PYTHON_API_HOST=[::]`; gunicorn binds `[::]:5000`, which is dual-stack (lesson 2). Railway's IPv4 healthcheck and nginx over IPv4 or IPv6 both work.

### Web UI (nginx) and the stale-upstream question

- The image's template (`/etc/nginx/templates/default.conf.template`, read from layer `sha256:7cd6305c…`) already proxies through a variable (`set $backend_upstream ${BACKEND_URL}; proxy_pass $backend_upstream;`). It re-resolves the name every 10 s, so a Backend redeploy with a new private IP is picked up. But it hard-codes `resolver 127.0.0.11 valid=10s ipv6=off;`, Docker's embedded DNS. On Railway that address has no resolver, so every `/api` call would fail.
- `services/web/05-railway-nginx.sh` runs from `/docker-entrypoint.d` before `20-envsubst-on-templates.sh`. It replaces only that line with `resolver <nameserver from /etc/resolv.conf> valid=10s;` (Railway: `[fd12::10]`; override `NGINX_RESOLVER`), with IPv6 answers allowed. It adds `set_real_ip_from` for private/loopback ranges plus `real_ip_header X-Forwarded-For; real_ip_recursive on;` (switch: `NGINX_TRUST_FORWARDED_FOR`). The Backend trusts `X-Real-IP` from private peers (`auth_session.get_client_ip`); without this, every visitor would share the proxy's IP in the login rate limits (`SECURITY_IP_MAX_ATTEMPTS`).
- The script is idempotent and leaves the file unchanged if a future template has no `resolver` line. Tested against the real template (output diff in the report). The SPA files and branding are untouched.
- `BACKEND_URL=http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:5000` is the value upstream's compose comment suggests for Railway.

### Redis tiers and Kafka

- **Redis** (cache): `--maxmemory 128mb --maxmemory-policy allkeys-lru`, `--save ''`, no AOF, no volume. Upstream calls this tier optional.
- **Redis Jobs**: `--appendonly yes --appendfsync everysec --save 60 1000 --maxmemory 512mb --maxmemory-policy noeviction`, with a volume at `/data`. Both have passwords (Railway base pattern); the clients build URLs with `quote()` (`app/config/redis_urls.py`). Keeping the instances separate, as upstream insists, means a full cache never evicts queued jobs.
- **Kafka**: KRaft combined node; listeners `PLAINTEXT://[::]:9092,CONTROLLER://[::]:9093` (lesson 14; confluent-kafka/librdkafka clients try IPv6 first); advertised `PLAINTEXT://kafka.railway.internal:9092`.
  - Quorum voters are `1@localhost:9093`, as in the image's own default `server.properties` (lesson 13: no self-resolution at boot).
  - Log dir is a subdirectory of the volume, so `lost+found` is not taken for a partition.
  - `RAILWAY_RUN_UID=0`, because the image user `appuser` cannot write the root-owned volume.
  - Heap and partition counts are the compose values. Topic partitions are 6/12/12/3 (base compose; the ghcr compose's 48/128/96/24 is sized for large installs). `CLUSTER_ID` is upstream's fixed value. The image formats the volume on first boot and logs "already formatted" afterwards.

### MCP Server

- There is no published image. The PyPI wheel `quantdinger-mcp==0.6.2` differs from the v5.8.4 `mcp_server/` source, which adds `submit_factor_benchmark` and an idempotency key on `compile_strategy_code`. So the build downloads the five files from the release commit and verifies their SHA-256, and installs the deps from `requirements.txt`: 29 packages, 43 wheel hashes for manylinux x86_64/aarch64 cp312, resolved with `pip download` for `mcp==1.28.1` as upstream pins `mcp>=1.28.1,<1.29`. It runs as uid 10001 with `python -m quantdinger_mcp.server`.
- Upstream exits at import without `QUANTDINGER_AGENT_TOKEN`, and that token only exists after the first login. `railway_mcp.py` therefore serves a stdlib placeholder until the variables are valid: `/.well-known/oauth-protected-resource` → 200 (healthcheck), everything else → 503 with the steps. It also covers an inbound token shorter than 32 characters, equal to the agent token, or a non-https public URL, all of which make upstream exit. This fails closed without failing the deploy (lesson 29).
- The real server: FastMCP (mcp 1.28.1) with a static bearer verifier (`QUANTDINGER_MCP_AUTH_TOKEN`, `secret(48)`) and `AuthSettings(resource_server_url=QUANTDINGER_MCP_PUBLIC_URL)`. It registers `/.well-known/oauth-protected-resource` (RFC 9728 path for a resource URL without a path) unauthenticated, and `/mcp` behind `RequireAuthMiddleware`. The host is `0.0.0.0`, so no DNS-rebinding allow-list applies (that only happens for 127.0.0.1/localhost). uvicorn on `::` would be IPv6-only (lesson 2).

### Admin, registration and safety defaults

- `ensure_admin_exists()` (API role only, `app/__init__.py`) creates the first user from `ADMIN_USER` / `ADMIN_PASSWORD` / `ADMIN_EMAIL` when `qd_users` is empty, pre-verified and with role admin. `init.sql` seeds no user. Later boots only re-sync while the stored hash is still `123456`, so a password changed in the app is never overwritten.
- `ENABLE_REGISTRATION=false`. Upstream defaults to `true`, and registration also needs SMTP verification codes.
- `LIVE_TRADING_ENABLED=false` (strategy save/start in live mode → 403, `routes/strategy.py`, `strategy_v2/deployment.py`). `AGENT_LIVE_TRADING_ENABLED=false` (upstream default).
- Billing, marketplace, USDT, USDC, Stripe and referrals: `false` (upstream defaults, explicit).
- `BROKER_ACCOUNTS_ENABLED=true` and `AGENT_GATEWAY_ENABLED=true` (upstream defaults). Users must be able to add exchange keys deliberately, and MCP needs the gateway.
- **Gap documented in README:** `/api/quick-trade/place-order` is **not** gated by `LIVE_TRADING_ENABLED`. Manual orders go out as soon as exchange keys are saved. README: trade-only keys without withdrawal rights, IP allow-lists, not investment advice.
- The optional AI pre-trade filter fails open when no provider is reachable (upstream `.env.example`). This is mentioned in the report, not in the README (length).

### Things deliberately left out

Mobile H5, the observability overlay, `env-sync`, Grafana credentials, SMTP/OAuth/Turnstile/Twilio configuration (Settings page or variables, user's choice), JEV keys, and the IBKR desktop gateway (needs TWS on a reachable machine).

## Services

The order below is the order of `template.json`. The workers share Backend's values by reference.

### Web

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/web`
- **Start command:** image default
- **Healthcheck:** `/health` (timeout 300 s) · **Public domain:** yes, target port 80 · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `QUANTDINGER_FRONTEND_IMAGE` | `ghcr.io/openbyteinc/quantdinger-frontend:5.8.4@sha256:fc993eb1eef5152097e95db8969691692b7c02272055fc801e2c603761c09b8d` | Web UI image (build argument), pinned to QuantDinger 5.8.4 by digest. Keep it on the same release as QUANTDINGER_BACKEND_IMAGE on Backend. |
| `PORT` | `80` | Port nginx listens on (public domain target and healthcheck). |
| `BACKEND_URL` | `http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:5000` | Backend API on the private network; nginx proxies /api/ to it and re-resolves the name every 10 s. |
| `NGINX_RESOLVER` | *(empty)* | Optional DNS server for nginx. Empty = the container's resolver from /etc/resolv.conf (Railway private DNS). |
| `NGINX_TRUST_FORWARDED_FOR` | `true` | Take the visitor IP from X-Forwarded-For sent by Railway's proxy (private addresses only), so login rate limits see real client IPs. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `10` | Seconds between SIGTERM and SIGKILL on redeploy. |

### Backend

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger api`
- **Pre-deploy:** `/usr/local/bin/railway-quantdinger migrate` (timeout 1200 s)
- **Healthcheck:** `/api/health/ready` (timeout 600 s) · **Public domain:** no · **Volume:** `/app/data` · **Restart:** ALWAYS · **Replicas:** 1

Owns every shared value; the eight workers reference these as `${{Backend.KEY}}`.

| Variable | Value | Description |
|---|---|---|
| `QUANTDINGER_BACKEND_IMAGE` | `ghcr.io/openbyteinc/quantdinger-backend:v5.8.4@sha256:3878e94a1344a979e98b689369ed3fafe51ed065c3d51b11782b7f3dd52d4e26` | Backend image every backend-image service is built from (build argument). Pinned to QuantDinger v5.8.4 by digest; change it here to upgrade, then redeploy Backend and all workers. |
| `TZ` | `UTC` | Time zone of all backend processes and Celery schedules (upstream's compose default is Asia/Shanghai). |
| `LOG_FORMAT` | `json` | Log format (json or text). |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR). |
| `SECRET_KEY` | `${{secret(64, "abcdef0123456789")}}` | JWT/session signing key, generated at deploy and shared by every backend process. Changing it signs everyone out. |
| `CREDENTIAL_ENCRYPTION_KEY` | `${{secret(64, "abcdef0123456789")}}` | Encrypts saved exchange/broker credentials and MFA secrets, generated at deploy. Never change it after saving credentials (they become unreadable). |
| `ADMIN_USER` | `admin` | Username of the first administrator, created on the first start (3-50 letters, digits or underscores). |
| `ADMIN_PASSWORD` | `${{secret(24, "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789")}}` | Password of the first administrator, generated at deploy. Used once to create the account; change your password in the app afterwards. |
| `ADMIN_EMAIL` | *(empty)* | Optional email of the first administrator (password recovery, notifications). |
| `ENABLE_REGISTRATION` | `false` | Public sign-up. Off: only the administrator can create users. Sign-up also needs SMTP for verification codes. |
| `LIVE_TRADING_ENABLED` | `false` | Allows strategies in live execution mode (real orders). Off by default; paper/signal mode only. Manual Quick Trade orders are NOT covered by this switch. |
| `AGENT_LIVE_TRADING_ENABLED` | `false` | Allows live orders from Agent Tokens (MCP and the agent API). Off by default (paper orders only). |
| `BROKER_ACCOUNTS_ENABLED` | `true` | Shows exchange/broker account settings in the UI (upstream default). Nothing trades until you save exchange API keys yourself. |
| `AGENT_GATEWAY_ENABLED` | `true` | Agent Gateway /api/agent/v1 (needed by the MCP Server). |
| `BILLING_ENABLED` | `false` | Credits/membership billing module (upstream default off). |
| `MARKETPLACE_ENABLED` | `false` | Strategy marketplace module (upstream default off). |
| `USDT_PAY_ENABLED` | `false` | USDT on-chain payment module (upstream default off). |
| `USDC_PAY_ENABLED` | `false` | USDC on-chain payment module (upstream default off). |
| `STRIPE_PAY_ENABLED` | `false` | Stripe payment module (upstream default off). |
| `REFERRAL_PROGRAM_ENABLED` | `false` | Referral rewards (upstream default off). |
| `QUANTDINGER_DEPLOYMENT_MODE` | `self_hosted` | Deployment mode (self_hosted, or saas for a multi-tenant service). |
| `OPENAPI_ENABLED` | `false` | Interactive API docs at /api/docs (off in production upstream). |
| `PYTHON_API_DEBUG` | `false` | Flask debug mode (never enable on a public instance). |
| `SKIP_AUTO_MIGRATE` | `true` | Processes do not migrate on start; Backend's pre-deploy command runs the migration. |
| `DB_TYPE` | `postgresql` | Database type. |
| `REDIS_DB` | `0` | Redis database of the cache. |
| `REDIS_CACHE_NAMESPACE` | `quantdinger:cache:v1` | Key prefix of the cache. |
| `CACHE_ENABLED` | `true` | Use the Redis cache. |
| `CELERY_TASKS_ENABLED` | `true` | Run AI jobs, backtests and maintenance through Celery (Redis Jobs). |
| `CELERY_BROKER_DB` | `0` | Redis Jobs database of the Celery broker. |
| `CELERY_RESULT_DB` | `1` | Redis Jobs database of the Celery results. |
| `KAFKA_EVENT_PUBLISH_ENABLED` | `true` | Publish bar-close, strategy and order events to Kafka. |
| `KAFKA_REPLICATION_FACTOR` | `1` | Topic replication factor (single Kafka node). |
| `KAFKA_MARKET_PARTITIONS` | `6` | Partitions of the market-bar topic (set before the first deploy; not changed later). |
| `KAFKA_STRATEGY_PARTITIONS` | `12` | Partitions of the strategy topics. |
| `KAFKA_ORDER_PARTITIONS` | `12` | Partitions of the order topics. |
| `KAFKA_DLQ_PARTITIONS` | `3` | Partitions of the dead-letter topic. |
| `MARKET_CATALOG_AUTO_SYNC` | `true` | Sync the market symbol catalog automatically. |
| `MARKET_CATALOG_SYNC_INTERVAL_SEC` | `86400` | Market catalog sync interval in seconds. |
| `LLM_PROVIDER` | `openrouter` | AI provider: openrouter, openai, google, deepseek, grok, minimax, atlascloud or custom (any OpenAI-compatible API). Optional: the app runs without AI keys. |
| `OPENROUTER_API_KEY` | *(empty)* | Optional. OpenRouter API key (LLM_PROVIDER=openrouter). |
| `OPENROUTER_MODEL` | `openai/gpt-5.4` | OpenRouter model id (upstream default). |
| `OPENAI_API_KEY` | *(empty)* | Optional. OpenAI API key (LLM_PROVIDER=openai). |
| `OPENAI_MODEL` | `gpt-5.4` | OpenAI model (upstream default). |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI API base URL. |
| `DEEPSEEK_API_KEY` | *(empty)* | Optional. DeepSeek API key (LLM_PROVIDER=deepseek). |
| `GOOGLE_API_KEY` | *(empty)* | Optional. Google Gemini API key (LLM_PROVIDER=google). |
| `GROK_API_KEY` | *(empty)* | Optional. xAI Grok API key (LLM_PROVIDER=grok). |
| `MINIMAX_API_KEY` | *(empty)* | Optional. MiniMax API key (LLM_PROVIDER=minimax). |
| `CUSTOM_API_URL` | *(empty)* | Optional. Base URL of any OpenAI-compatible API, ending in /v1 (LLM_PROVIDER=custom). |
| `CUSTOM_API_KEY` | *(empty)* | Optional. API key for CUSTOM_API_URL. |
| `CUSTOM_MODEL` | *(empty)* | Optional. Model name for CUSTOM_API_URL. |
| `TAVILY_API_KEYS` | *(empty)* | Optional. Tavily key(s) for AI web/news search (comma-separated). |
| `FINNHUB_API_KEY` | *(empty)* | Optional. Finnhub key (US stock quotes, profiles, news). |
| `TWELVE_DATA_API_KEY` | *(empty)* | Optional. Twelve Data key (CN/HK stock candles from overseas servers). |
| `QD_SCHEMA_WAIT_SECONDS` | `900` | Template wrapper: how long workers wait for Backend's migration before starting anyway. |
| `QD_THREAD_CAP` | `4` | Template wrapper: upper limit for native thread pools (numpy/BLAS), also capped by the service's CPU quota. |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Postgres connection string (private network). |
| `REDIS_HOST` | `${{Redis.REDISHOST}}` | Cache Redis host (private network). |
| `REDIS_PORT` | `${{Redis.REDISPORT}}` | Cache Redis port. |
| `REDIS_PASSWORD` | `${{Redis.REDIS_PASSWORD}}` | Cache Redis password. |
| `CELERY_REDIS_HOST` | `${{Redis Jobs.REDISHOST}}` | Durable job Redis host (Celery broker and results). |
| `CELERY_REDIS_PORT` | `${{Redis Jobs.REDISPORT}}` | Durable job Redis port. |
| `CELERY_REDIS_PASSWORD` | `${{Redis Jobs.REDIS_PASSWORD}}` | Durable job Redis password. |
| `KAFKA_BOOTSTRAP_SERVERS` | `${{Kafka.RAILWAY_PRIVATE_DOMAIN}}:9092` | Kafka broker (private network). |
| `FRONTEND_URL` | `https://${{Web.RAILWAY_PUBLIC_DOMAIN}}` | Public web origin (CORS, OAuth redirects). Change it when you add a custom domain to Web. |
| `QD_PROCESS_ROLE` | `api` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `true` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `2` | Connections this process keeps open. |
| `DB_POOL_MAX` | `12` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-api` | Name shown in pg_stat_activity. |
| `PORT` | `5000` | Port Railway health-checks (gunicorn listens on [::]:5000). Never add a public domain: Web proxies /api. |
| `PYTHON_API_HOST` | `[::]` | Bind address of gunicorn (dual-stack IPv4/IPv6 for the private network). |
| `PYTHON_API_PORT` | `5000` | Port of the API (Web proxies to it). |
| `QUANTDINGER_ENV_FILE` | `/app/data/.env` | Settings file on the Backend volume (the Settings page writes here). Railway variables are written into it at every start. |
| `INDICATOR_PREVIEW_DIR` | `/app/data/indicator_previews` | Indicator preview images (on the volume). |
| `PROMETHEUS_MULTIPROC_DIR` | `/tmp/quantdinger-prometheus` | Prometheus multiprocess metrics directory (cleared on start). |
| `GUNICORN_WORKERS` | `2` | Gunicorn worker processes. |
| `GUNICORN_THREADS` | `4` | Threads per gunicorn worker. |
| `GUNICORN_MAX_REQUESTS` | `800` | Requests before a gunicorn worker is recycled. |
| `GUNICORN_MAX_REQUESTS_JITTER` | `100` | Random jitter for the recycling above. |
| `DB_POOL_ACQUIRE_TIMEOUT` | `10` | Seconds to wait for a free database connection. |
| `MARKET_EXECUTOR_WORKERS` | `6` | Parallel market-data fetches per request. |
| `PORTFOLIO_EXECUTOR_WORKERS` | `3` | Parallel portfolio fetches per request. |
| `RESOURCE_FD_COOLDOWN_SEC` | `180` | Cooldown after file-descriptor pressure. |
| `PORTFOLIO_MONITOR_DUE_BATCH_LIMIT` | `5` | Portfolio monitor batch size. |
| `BACKTEST_KLINE_CACHE_MAX_BYTES` | `134217728` | Per-process candle cache (128 MiB). |
| `STRATEGY_SHARED_FRAME_CACHE_MAX_BYTES` | `268435456` | Per-process strategy frame cache (256 MiB). |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `45` | Seconds between SIGTERM and SIGKILL on redeploy (graceful worker shutdown, as upstream's stop_grace_period). |

### Trading Worker

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger trading`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `trading` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `4` | Connections this process keeps open. |
| `DB_POOL_MAX` | `32` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-trading` | Name shown in pg_stat_activity. |
| `KAFKA_CLIENT_ID` | `quantdinger-trading` | Kafka client id. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `45` | Seconds between SIGTERM and SIGKILL on redeploy (graceful worker shutdown, as upstream's stop_grace_period). |

### Strategy Dispatcher

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger strategy-dispatcher`
- **Pre-deploy:** `/usr/local/bin/railway-quantdinger kafka-topics` (timeout 1200 s)
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `strategy-dispatcher` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `1` | Connections this process keeps open. |
| `DB_POOL_MAX` | `4` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-strategy-dispatcher` | Name shown in pg_stat_activity. |
| `KAFKA_CLIENT_ID` | `quantdinger-strategy-dispatcher` | Kafka client id. |
| `KAFKA_STRATEGY_DISPATCH_GROUP_ID` | `quantdinger-strategy-dispatch-v1` | Kafka consumer group. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `45` | Seconds between SIGTERM and SIGKILL on redeploy (graceful worker shutdown, as upstream's stop_grace_period). |

### Strategy Evaluator

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger strategy-evaluator`
- **Pre-deploy:** `/usr/local/bin/railway-quantdinger kafka-topics` (timeout 1200 s)
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `strategy-evaluator` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `2` | Connections this process keeps open. |
| `DB_POOL_MAX` | `16` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-strategy-evaluator` | Name shown in pg_stat_activity. |
| `KAFKA_CLIENT_ID` | `quantdinger-strategy-evaluator` | Kafka client id. |
| `KAFKA_STRATEGY_EVALUATOR_GROUP_ID` | `quantdinger-strategy-evaluator-active-v1` | Kafka consumer group. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `45` | Seconds between SIGTERM and SIGKILL on redeploy (graceful worker shutdown, as upstream's stop_grace_period). |

### Kafka Audit Worker

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger kafka-audit`
- **Pre-deploy:** `/usr/local/bin/railway-quantdinger kafka-topics` (timeout 1200 s)
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `kafka-audit` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `1` | Connections this process keeps open. |
| `DB_POOL_MAX` | `3` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-kafka-audit` | Name shown in pg_stat_activity. |
| `KAFKA_AUDIT_GROUP_ID` | `quantdinger-runtime-audit-v1` | Kafka consumer group. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `45` | Seconds between SIGTERM and SIGKILL on redeploy (graceful worker shutdown, as upstream's stop_grace_period). |

### Scheduler

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger scheduler`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `scheduler` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `2` | Connections this process keeps open. |
| `DB_POOL_MAX` | `12` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-scheduler` | Name shown in pg_stat_activity. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `45` | Seconds between SIGTERM and SIGKILL on redeploy (graceful worker shutdown, as upstream's stop_grace_period). |

### Celery Worker

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger celery`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `celery` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `2` | Connections this process keeps open. |
| `DB_POOL_MAX` | `12` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-celery-worker` | Name shown in pg_stat_activity. |
| `CELERY_CONCURRENCY` | `2` | Celery processes for the ai and maintenance queues. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Seconds between SIGTERM and SIGKILL on redeploy (lets running tasks finish). |

### Celery Backtest Worker

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger celery-backtest`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `celery` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `2` | Connections this process keeps open. |
| `DB_POOL_MAX` | `12` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-celery-backtest-worker` | Name shown in pg_stat_activity. |
| `CELERY_BACKTEST_CONCURRENCY` | `1` | Parallel backtests (each needs up to CELERY_BACKTEST_MAX_MEMORY_KB). |
| `CELERY_BACKTEST_MAX_MEMORY_KB` | `1572864` | Memory limit per backtest process in KiB (1.5 GiB); the process is replaced after each task. |
| `CELERY_MAX_TASKS_PER_CHILD` | `1` | Recycle the backtest process after every task (upstream setting). |
| `CELERY_MAX_MEMORY_PER_CHILD_KB` | `1572864` | Same limit for the Celery app configuration. |
| `BACKTEST_KLINE_CACHE_MAX_BYTES` | `134217728` | Per-process candle cache (128 MiB). |
| `STRATEGY_SHARED_FRAME_CACHE_MAX_BYTES` | `268435456` | Per-process strategy frame cache (256 MiB). |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Seconds between SIGTERM and SIGKILL on redeploy (lets running tasks finish). |

### Celery Beat

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/backend`
- **Start command:** `/usr/local/bin/railway-quantdinger celery-beat`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

Also sets the 57 shared variables as `${{Backend.KEY}}` references and the 9 connection variables exactly as Backend (see Backend). Own values:

| Variable | Value | Description |
|---|---|---|
| `QD_PROCESS_ROLE` | `celery` | Process role (the start command enforces it). |
| `STRATEGY_COMMANDS_ENABLED` | `false` | Accepts strategy start/stop commands (API process only). |
| `DB_POOL_MIN` | `1` | Connections this process keeps open. |
| `DB_POOL_MAX` | `2` | Connection pool limit of this process (keep the sum of all pools below Postgres max_connections=200). |
| `DB_APPLICATION_NAME` | `quantdinger-celery-beat` | Name shown in pg_stat_activity. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `45` | Seconds between SIGTERM and SIGKILL on redeploy (graceful worker shutdown, as upstream's stop_grace_period). |

### MCP Server

- **Source:** repo `baranberkay96/quantdinger-railway`, root `/services/mcp`
- **Start command:** image default
- **Healthcheck:** `/.well-known/oauth-protected-resource` (timeout 300 s) · **Public domain:** yes, target port 7800 · **Volume:** none · **Restart:** ALWAYS · **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `PORT` | `7800` | Port Railway health-checks (MCP endpoint: /mcp). |
| `QUANTDINGER_AGENT_TOKEN` | *(empty)* | Agent Token (qd_agent_...) the MCP server acts with. Empty until you issue one: QuantDinger -> Profile -> My Agent Token (paper-only recommended). Until then the endpoint answers 503. |
| `QUANTDINGER_MCP_AUTH_TOKEN` | `${{secret(48, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Bearer token MCP clients must send (Authorization: Bearer ...), generated at deploy. Keep it secret. |
| `QUANTDINGER_BASE_URL` | `http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:5000` | QuantDinger API on the private network. |
| `QUANTDINGER_MCP_PUBLIC_URL` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | Public https origin of this service (change it when you add a custom domain). |
| `QUANTDINGER_MCP_TRANSPORT` | `streamable-http` | MCP transport (streamable-http on /mcp, or sse). |
| `QUANTDINGER_MCP_HOST` | `0.0.0.0` | Bind address (IPv4; Railway's proxy and healthcheck connect over IPv4). |
| `QUANTDINGER_MCP_PORT` | `7800` | Port of the MCP server. |
| `QUANTDINGER_TIMEOUT_S` | `60` | Timeout for calls to the QuantDinger API, in seconds. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `10` | Seconds between SIGTERM and SIGKILL on redeploy. |

### Postgres

- **Source:** image `ghcr.io/railwayapp-templates/postgres-ssl:18`
- **Start command:** `/usr/bin/tini -g -- /usr/local/bin/wrapper.sh postgres -p 5432 -c listen_addresses=* -c max_connections=200 -c shared_buffers=256MB`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** `/var/lib/postgresql/data` · **Restart:** ON_FAILURE (10) · **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `PGDATA` | `/var/lib/postgresql/data/pgdata` | Data directory inside the volume (Railway base layout). |
| `PGHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Private hostname of this database. |
| `PGPORT` | `5432` | Postgres port. |
| `PGUSER` | `${{POSTGRES_USER}}` | User for the Data panel and the other services. |
| `PGPASSWORD` | `${{POSTGRES_PASSWORD}}` | Password for the Data panel and the other services. |
| `PGDATABASE` | `${{POSTGRES_DB}}` | Database for the Data panel and the other services. |
| `POSTGRES_USER` | `postgres` | Superuser created on first boot. |
| `POSTGRES_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Superuser password, generated at deploy (letters only, safe in URLs). |
| `POSTGRES_DB` | `railway` | Database created on first boot (QuantDinger's tables live here). |
| `DATABASE_URL` | `postgresql://${{PGUSER}}:${{POSTGRES_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{PGDATABASE}}` | Private connection string (Railway convention). |
| `SSL_CERT_DAYS` | `820` | Validity of the self-signed TLS certificate. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Time Postgres gets to shut down cleanly on redeploy. |

### Redis

- **Source:** image `redis:8.2`
- **Start command:** `/bin/sh -c "exec docker-entrypoint.sh redis-server --requirepass $REDIS_PASSWORD --save '' --appendonly no --maxmemory $REDIS_MAXMEMORY --maxmemory-policy allkeys-lru"`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** none · **Restart:** ON_FAILURE (10) · **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `REDISHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Private hostname of this Redis. |
| `REDISPORT` | `6379` | Port Redis listens on. |
| `REDISUSER` | `default` | Redis user. |
| `REDIS_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Password, generated at deploy. |
| `REDISPASSWORD` | `${{REDIS_PASSWORD}}` | Alias of REDIS_PASSWORD. |
| `REDIS_URL` | `redis://${{ REDISUSER }}:${{ REDIS_PASSWORD }}@${{ REDISHOST }}:${{ REDISPORT }}` | Private connection string. |
| `REDIS_MAXMEMORY` | `128mb` | Memory cap of the cache; least recently used keys are evicted (upstream: 128mb, allkeys-lru, no persistence). |

### Redis Jobs

- **Source:** image `redis:8.2`
- **Start command:** `/bin/sh -c "rm -rf $RAILWAY_VOLUME_MOUNT_PATH/lost+found/ && exec docker-entrypoint.sh redis-server --requirepass $REDIS_PASSWORD --dir $RAILWAY_VOLUME_MOUNT_PATH --appendonly yes --appendfsync everysec --save 60 1000 --maxmemory $REDIS_MAXMEMORY --maxmemory-policy noeviction"`
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** `/data` · **Restart:** ON_FAILURE (10) · **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `REDISHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Private hostname of this Redis. |
| `REDISPORT` | `6379` | Port Redis listens on. |
| `REDISUSER` | `default` | Redis user. |
| `REDIS_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Password, generated at deploy. |
| `REDISPASSWORD` | `${{REDIS_PASSWORD}}` | Alias of REDIS_PASSWORD. |
| `REDIS_URL` | `redis://${{ REDISUSER }}:${{ REDIS_PASSWORD }}@${{ REDISHOST }}:${{ REDISPORT }}` | Private connection string. |
| `REDIS_MAXMEMORY` | `512mb` | Memory cap of the job queue. noeviction: when full, new jobs are refused instead of silently dropping queued ones (upstream: 512mb, AOF everysec). |

### Kafka

- **Source:** image `apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837`
- **Start command:** image default
- **Healthcheck:** none (no HTTP port) · **Public domain:** no · **Volume:** `/var/lib/kafka/data` · **Restart:** ALWAYS · **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `KAFKA_NODE_ID` | `1` | Node id (single combined broker/controller). |
| `KAFKA_PROCESS_ROLES` | `broker,controller` | KRaft combined mode (no ZooKeeper). |
| `KAFKA_LISTENERS` | `PLAINTEXT://[::]:9092,CONTROLLER://[::]:9093` | Listeners on all IPv6 and IPv4 addresses (librdkafka clients try IPv6 first). |
| `KAFKA_ADVERTISED_LISTENERS` | `PLAINTEXT://${{RAILWAY_PRIVATE_DOMAIN}}:9092` | Address clients are told to use (private network only). |
| `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP` | `CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT` | Listener protocols (private network, no TLS). |
| `KAFKA_CONTROLLER_LISTENER_NAMES` | `CONTROLLER` | Controller listener. |
| `KAFKA_INTER_BROKER_LISTENER_NAME` | `PLAINTEXT` | Inter-broker listener. |
| `KAFKA_CONTROLLER_QUORUM_VOTERS` | `1@localhost:9093` | Controller quorum. localhost on purpose: a service cannot resolve its own private name while it boots. |
| `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` | `1` | Single node. |
| `KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR` | `1` | Single node. |
| `KAFKA_TRANSACTION_STATE_LOG_MIN_ISR` | `1` | Single node. |
| `KAFKA_SHARE_COORDINATOR_STATE_TOPIC_REPLICATION_FACTOR` | `1` | Single node. |
| `KAFKA_SHARE_COORDINATOR_STATE_TOPIC_MIN_ISR` | `1` | Single node. |
| `KAFKA_TRANSACTION_STATE_LOG_NUM_PARTITIONS` | `12` | Upstream compose value. |
| `KAFKA_OFFSETS_TOPIC_NUM_PARTITIONS` | `12` | Upstream compose value. |
| `KAFKA_NUM_PARTITIONS` | `6` | Partitions of auto-created topics (upstream compose value). |
| `KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS` | `0` | Start consumer groups immediately. |
| `KAFKA_LOG_DIRS` | `/var/lib/kafka/data/kraft-combined-logs` | Data directory inside the volume (a subdirectory, so the volume's lost+found is not taken for a partition). |
| `KAFKA_HEAP_OPTS` | `-Xms256m -Xmx768m` | JVM heap (upstream compose value). |
| `CLUSTER_ID` | `MkU3OEVBNTcwNTJENDM2Qk` | KRaft cluster id used to format the volume on first boot (upstream compose value; not a secret). Do not change it after the first deploy. |
| `RAILWAY_RUN_UID` | `0` | Run as root so Kafka can write to the volume (mounted root-owned). |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Time Kafka gets to shut down cleanly on redeploy. |


## Improvements over market templates

There is no market template. Compared with running upstream's compose files as they are:

- No default credentials. Upstream's `.env.example` ships `ADMIN_PASSWORD=123456`. Here the admin password, `SECRET_KEY`, `CREDENTIAL_ENCRYPTION_KEY`, the database and Redis passwords and the MCP bearer token are all generated. The API refuses to start with `123456` or a short password.
- Paper-only and admin-only by default (`LIVE_TRADING_ENABLED=false`, `ENABLE_REGISTRATION=false`). Upstream defaults both to `true`.
- The settings file is kept consistent with Railway variables, so neither the UI flags nor a Settings save can fall back to example hosts or credentials.
- Migrations and Kafka topic creation run as pre-deploy commands with retries, and workers wait for the schema instead of crash-looping.
- The web UI's Docker-only DNS resolver is replaced, so `/api` works on Railway and follows Backend redeploys. Real client IPs reach the login rate limits.
- The MCP server is included (behind a compose profile upstream) and runs the v5.8.4 source, not the older PyPI wheel. A placeholder runs until it is configured.
- Kafka and the API listen dual-stack. Native thread pools are capped to the CPU quota. Images are pinned by digest, and the MCP dependencies are pinned by hash.

## Scaling

- **Backend:** vertical; raise `GUNICORN_WORKERS` (each worker runs the API's background threads) or `GUNICORN_THREADS`.
- **Celery Worker:** `CELERY_CONCURRENCY` (default 2) for AI jobs. **Celery Backtest Worker:** `CELERY_BACKTEST_CONCURRENCY` × up to 1.5 GiB each.
- **Trading Worker, Strategy Evaluator, Strategy Dispatcher:** upstream supports replicas (leases and Kafka consumer groups), but the template keeps 1. Load-test before adding replicas (`numReplicas` > 1 needs a region in Railway's multi-region config).
- **Celery Beat, Scheduler, Kafka Audit Worker:** keep 1.
- **Database connections:** the pools add up to about 141 at most (API 2×12, trading 32, scheduler 12, celery ~24, backtest 12, evaluator 16, dispatcher 4, audit 3, beat 2, migration 2). Postgres runs with `max_connections=200`. Raise both together.

## Resource estimate

Prices: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month. **Not measured** (no container run). These figures are derived from the processes each service starts: every backend-image process imports the full Flask app (pandas, numpy, akshare, litellm, exchange SDKs).

| Service | Idle RAM / vCPU | Typical RAM / vCPU | Notes |
|---|---|---|---|
| Web | 0.02 GB / 0.001 | 0.03 GB / 0.01 | nginx |
| Backend | 0.80 GB / 0.03 | 1.20 GB / 0.20 | 2 gunicorn workers + background threads |
| Trading Worker | 0.35 GB / 0.02 | 0.60 GB / 0.15 | grows with running strategies |
| Strategy Dispatcher | 0.30 GB / 0.01 | 0.35 GB / 0.03 | |
| Strategy Evaluator | 0.35 GB / 0.01 | 0.50 GB / 0.10 | 16 evaluator threads |
| Kafka Audit Worker | 0.30 GB / 0.01 | 0.30 GB / 0.01 | |
| Scheduler | 0.35 GB / 0.02 | 0.45 GB / 0.05 | market data, portfolio monitor |
| Celery Worker | 0.75 GB / 0.01 | 1.10 GB / 0.15 | main + 2 children |
| Celery Backtest Worker | 0.45 GB / 0.005 | 1.50 GB / 0.30 (burst) | child recycled per task |
| Celery Beat | 0.20 GB / 0.005 | 0.20 GB / 0.005 | |
| MCP Server | 0.04 GB / 0.001 | 0.08 GB / 0.01 | placeholder until configured |
| Postgres | 0.15 GB / 0.01 | 0.50 GB / 0.10 | volume ~1 GB after seeding, a few GB typical |
| Redis / Redis Jobs | 0.01 + 0.01 GB | 0.05 + 0.10 GB | |
| Kafka | 0.50 GB / 0.02 | 0.70 GB / 0.05 | heap ≤768 MB, volume grows with retention (3–30 days) |

- **Idle ≈ $50/month** (≈4.6 GB × $10 + ≈0.15 vCPU × $20 + ≈1.5 GB volumes).
- **Light use ≈ $90/month** (≈7 GB × $10 + ≈0.9 vCPU × $20 + ≈5 GB volumes); backtest bursts on top.
- **Minimum plan: Hobby.** Trial's 1 GB per service is too small for Backend, Celery and backtests. Model usage is billed by the AI provider. Outbound SMTP needs Pro.

## Verification checklist

1. **Builds:** Backend and every worker log `[railway] self-test ok`. The MCP build prints `quantdinger-mcp 0.6.2 … tools` after `sha256sum -c` of the five files. The Web build is a single `COPY`.
2. **Pre-deploy:** Backend logs `[migration] … all components complete` (later deploys: `unchanged, skipped`). Dispatcher, Evaluator and Audit log `Kafka topic created` (or `already exists`) and `kafka topics: done`.
3. **Kafka:** logs `Running in KRaft mode`, formatting on the first boot (`already formatted` after a redeploy), and the broker started. No `lost+found` error.
4. **Backend health:** `/api/health/ready` returns 200 with `postgres` and `celery_broker` true. Logs show `env file /app/data/.env: created from env.example` (first boot), `Created admin user: admin`, and gunicorn on `[::]:5000`.
5. **Workers:** each logs `schema: current`, then its role. From a Backend shell, `curl -s localhost:5000/api/health/workers` lists `trading`, `scheduler`, `celery`, `kafka-audit`, `strategy-dispatcher` and `strategy-evaluator` heartbeats as healthy.
6. **Web:** the log shows `05-railway-nginx.sh: nginx resolver [fd12::10] …`. `https://{web-domain}/health` returns OK. `https://{web-domain}/api/health` returns JSON (proxied).
7. **Login:** `ADMIN_USER` / `ADMIN_PASSWORD` from Backend → Variables work. `123456` does not. There is no register link; `POST /api/auth/register` returns "Registration is disabled".
8. **Flags:** the Settings page shows registration, live trading and billing off. Saving any setting and reloading still works (no `redis`/`localhost:29092` errors in Backend logs).
9. **Live gate:** create a strategy in live mode, or start one: the API answers 403 `strategyV2.liveTradingDisabled`. A paper/signal strategy starts, and the Trading Worker and Evaluator pick it up (Kafka consumer logs).
10. **AI job:** set `OPENROUTER_API_KEY` (or another provider) on Backend, redeploy, and run an AI analysis. The Celery Worker log shows a `fast_analysis` task succeeding. Run a backtest: the Celery Backtest Worker log shows the task and its child being replaced.
11. **Client IP:** after a failed login from your browser, the Backend log or the security audit shows your public IP, not a 10.x/fd… address.
12. **MCP:** `https://{mcp-domain}/.well-known/oauth-protected-resource` returns 200 `inactive`, and `/mcp` returns 503 with the steps. Issue a paper-only Agent Token, set `QUANTDINGER_AGENT_TOKEN`, and redeploy. The metadata now lists `resource: https://{mcp-domain}/`. `/mcp` without a token returns 401. A client with `Authorization: Bearer {QUANTDINGER_MCP_AUTH_TOKEN}` can call `whoami` and `check_health`.
13. **Redeploy Backend:** Web keeps proxying (re-resolved within 10 s). The login, strategies and Settings-page values survive. The env file log shows `0 value(s) set` when nothing changed.
14. **Redeploy Redis Jobs and Kafka:** queued Celery jobs and topics persist (volumes).

## Open questions

- **Not deployed and no Docker build** (instruction). Verified statically: registry manifests, configs and layers; tag source; `sh -n`; `py_compile`; the wrapper's logic against fakes and a local PostgreSQL 15; the nginx hook against the real template; the MCP placeholder over HTTP; JSON and reference checks.
- **nginx `-t`** of the rewritten config was not run (no nginx locally). The directives used (`resolver [IPv6]`, `set_real_ip_from`, `real_ip_header`, `real_ip_recursive`) are standard, and the official nginx image includes the realip module. Railway's resolver address is taken from `/etc/resolv.conf`; `fd12::10` is expected.
- **Kafka 4.3.1 with `[::]` listeners** and `localhost` voters on Railway is untested. Also untested: librdkafka's IPv6-first connection to `kafka.railway.internal`, and whether `RAILWAY_RUN_UID=0` is needed (the image user is `appuser`).
- **Railway pre-deploy containers:** the migration and topic creation in a separate container are as documented by Railway but unverified for this image. Pre-deploy has no volume, which these commands do not need.
- **Memory** per worker is estimated; upstream's production compose caps workers at 0.5–3 GB.
- **Quick Trade** is not gated by `LIVE_TRADING_ENABLED` in 5.8.4. It might be worth asking upstream whether `BROKER_ACCOUNTS_ENABLED=false` should also block saving credentials server-side; today it is only a UI capability flag.
- **Frontend bundle** not audited for analytics or telemetry. **Licence:** publishing a kickback-earning template with the source-available web UI was the user's explicit decision. Open Byte Inc. can revoke the licence or object, so watch for that.
- **Upstream pace:** a release almost daily (v5.7.6 → v5.8.4 in 12 days). Re-check migrations, the env.example keys and the nginx template before bumping, and keep the backend and web UI on one release.
