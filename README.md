# Deploy and Host QuantDinger with Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/quantdinger-v5-ai-trading-research?referralCode=20H68q)

QuantDinger is a self-hosted AI trading research platform: AI market analysis, Python strategies, factor research, backtesting, paper and live trading, monitoring and an MCP server for AI agents. This community template runs release v5.8.4 as upstream's full production stack, with paper trading only by default.

**Licence notice.** The QuantDinger web UI (and the H5 mobile client, not included here) is published by Open Byte Inc. under the QuantDinger Frontend Source-Available License. That licence is free only for non-commercial use, is revocable, and requires all "Powered by QuantDinger" branding to stay in place. If you run QuantDinger commercially, you need a commercial licence from Open Byte Inc. (support@quantdinger.com). The backend, workers and MCP server are Apache-2.0. This is a community template, not affiliated with or endorsed by Open Byte Inc. This is not legal advice; read the licences yourself.

**Not investment advice.** This template hosts software. Backtests, AI output and paper results do not predict real returns. Live trading can lose money, and that risk is entirely yours.

## About Hosting QuantDinger

QuantDinger is not a single container. The API serves the web UI. Strategies run in a separate trading worker. Bar-driven strategies are dispatched and evaluated through Kafka. AI jobs and backtests go through Celery, with a durable Redis that never evicts jobs. A scheduler handles market data and portfolio monitoring. This template deploys that stack as upstream's docker-compose describes it: 15 Railway services, private networking, volumes for the database, the job queue and Kafka, and the database migration before the API starts. Only the web UI and the token-protected MCP endpoint are public. The first administrator is created from generated variables, so there is no default password.

## Common Use Cases

- Research markets with AI analysis using your own OpenAI-compatible model key
- Write Python strategies and indicators, then backtest them on crypto, US, HK and other markets
- Paper-trade strategies against live market data before deciding about real money
- Let AI agents (Cursor, Claude, Codex) research, backtest and paper-trade through the MCP server
- Run a private quant workspace for yourself or a small team

## Dependencies for QuantDinger Hosting

- QuantDinger backend v5.8.4 (`ghcr.io/openbyteinc/quantdinger-backend`, Apache-2.0): API, eight workers and migrations
- QuantDinger web UI 5.8.4 (`ghcr.io/openbyteinc/quantdinger-frontend`, source-available licence)
- QuantDinger MCP server (built from the v5.8.4 source, Apache-2.0)
- PostgreSQL 18
- Redis 8.2, two instances: a cache and durable jobs
- Apache Kafka 4.3.1 (single-node KRaft)

### Deployment Dependencies

- Source and releases: https://github.com/OpenByteInc/QuantDinger/releases/tag/v5.8.4
- Upstream compose stack: https://github.com/OpenByteInc/QuantDinger/blob/v5.8.4/docker-compose.yml
- Configuration reference: https://github.com/OpenByteInc/QuantDinger/blob/v5.8.4/docs/deployment/CONFIGURATION_REFERENCE.md
- First run: https://github.com/OpenByteInc/QuantDinger/blob/v5.8.4/docs/getting-started/FIRST_RUN.md
- Agent Gateway and MCP: https://github.com/OpenByteInc/QuantDinger/blob/v5.8.4/docs/agent/AGENT_QUICKSTART.md
- Web UI licence: https://github.com/OpenByteInc/QuantDinger-Vue/blob/main/LICENSE
- Trademark policy: https://github.com/OpenByteInc/QuantDinger/blob/v5.8.4/TRADEMARKS.md

### Implementation Details

| Service | Role | Public |
|---|---|---|
| Web | Web UI (nginx), proxies `/api` to Backend | **yes** |
| Backend | Flask API (gunicorn); pre-deploy runs the migration | no |
| Trading Worker | Strategy runtimes, order execution, position sync | no |
| Strategy Dispatcher / Strategy Evaluator | Kafka-driven bar-close strategy evaluation | no |
| Kafka Audit Worker | Runtime event audit trail | no |
| Scheduler | Market data, portfolio monitor, periodic jobs | no |
| Celery Worker / Celery Backtest Worker / Celery Beat | AI jobs, maintenance, backtests (1.5 GB cap each), schedules | no |
| MCP Server | MCP endpoint `/mcp`, bearer token required | **yes** |
| Postgres, Redis, Redis Jobs, Kafka | Database, cache (LRU), durable job queue (AOF, no eviction), event backbone | no |

**First login**

1. Wait until Backend is healthy. The first deploy builds the images, migrates the database and seeds the market catalog, which takes a few minutes.
2. Open Backend → Variables and copy `ADMIN_USER` (default `admin`) and `ADMIN_PASSWORD` (generated).
3. Open the Web domain, sign in and change the password under your profile. Public sign-up is off.

**Safety defaults**

- Live trading is off. `LIVE_TRADING_ENABLED=false` blocks live-mode strategies, and `AGENT_LIVE_TRADING_ENABLED=false` keeps agent tokens paper-only.
- Billing, payments, marketplace and referrals are off.
- **Manual Quick Trade orders are not covered by these switches.** They go to the exchange as soon as you save exchange API keys.
- Create **trade-only API keys without withdrawal rights**, restrict them by IP where the exchange allows, and start small.
- Change the switches in Railway → Backend → Variables. Railway variables override the Settings page at every restart.

**AI and data keys (optional)**

The stack runs without any key. To use AI analysis, set `LLM_PROVIDER` and one key on **Backend** (all workers reference it): `OPENROUTER_API_KEY` (default provider), `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `GOOGLE_API_KEY`, `GROK_API_KEY`, `MINIMAX_API_KEY`, or `CUSTOM_API_URL` + `CUSTOM_API_KEY` + `CUSTOM_MODEL` for any OpenAI-compatible endpoint. Optional data keys are `TAVILY_API_KEYS`, `FINNHUB_API_KEY` and `TWELVE_DATA_API_KEY`. Then redeploy. Keys entered only on the Settings page reach the API process but not the workers, so prefer Railway variables. Model usage is billed by your provider.

**MCP**

The MCP endpoint answers 503 until you connect it:

1. In QuantDinger, open your profile and issue an Agent Token. Paper-only is recommended.
2. Paste it into MCP Server → `QUANTDINGER_AGENT_TOKEN` and redeploy MCP Server.
3. Point your client at `https://{mcp-domain}/mcp` with the header `Authorization: Bearer {QUANTDINGER_MCP_AUTH_TOKEN}`.

**Scaling and versions**

- Give memory to the Celery Backtest Worker for parallel backtests (`CELERY_BACKTEST_CONCURRENCY`).
- Raise `CELERY_CONCURRENCY` for more AI jobs.
- Keep the sum of the `DB_POOL_MAX` values below Postgres `max_connections=200`.
- Images are pinned to v5.8.4 by digest. To upgrade, change `QUANTDINGER_BACKEND_IMAGE` on Backend and `QUANTDINGER_FRONTEND_IMAGE` on Web to the same new release, then redeploy all services. Read upstream's release notes first.
- Email (SMTP) needs Railway's Pro plan for outbound mail.

**Cost (estimate):** about $50/month idle and $90/month in light use (≈5–7 GB RAM across 15 services). Hobby plan or higher.

### Why Deploy QuantDinger on Railway?

Railway runs QuantDinger's full worker topology without managing servers. Private networking keeps Postgres, Redis, Kafka and the API off the internet. Volumes keep strategies, jobs and events across redeploys. Workers and memory scale from the dashboard, so you can start in paper mode and grow the stack only when you need it.
