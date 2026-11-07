#!/usr/local/bin/python3
"""Start wrapper for the QuantDinger MCP server on Railway.

Upstream's server (mcp_server/src/quantdinger_mcp/server.py) exits at import when
QUANTDINGER_AGENT_TOKEN is missing, and on a public listener it refuses to start without an
inbound bearer token of 32+ characters and an https public URL. The Agent Token can only be
issued in QuantDinger after the first login, so on a fresh deploy this wrapper serves a small
placeholder instead of crash-looping: the health path answers 200, everything else 503 with
the steps to enable the endpoint. Once the variables are valid it execs the real server.
"""
from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HEALTH_PATH = "/.well-known/oauth-protected-resource"
MIN_AUTH_TOKEN = 32
DEFAULT_PORT = 7800


def log(message: str) -> None:
    print(f"[railway] {message}", file=sys.stderr, flush=True)


def listen_port(env: dict) -> int:
    for key in ("QUANTDINGER_MCP_PORT", "PORT"):
        raw = (env.get(key) or "").strip()
        if raw.isdigit() and 0 < int(raw) < 65536:
            return int(raw)
    return DEFAULT_PORT


def problems(env: dict) -> list[str]:
    """Return why the real server cannot run yet (empty list = ready)."""
    found = []
    agent = (env.get("QUANTDINGER_AGENT_TOKEN") or "").strip()
    inbound = (env.get("QUANTDINGER_MCP_AUTH_TOKEN") or "").strip()
    public_url = (env.get("QUANTDINGER_MCP_PUBLIC_URL") or "").strip()
    if not agent:
        found.append("QUANTDINGER_AGENT_TOKEN is empty: sign in to QuantDinger, open Profile -> My Agent Token, "
                     "issue a paper-only token and paste it into MCP Server -> Variables")
    if len(inbound) < MIN_AUTH_TOKEN:
        found.append(f"QUANTDINGER_MCP_AUTH_TOKEN must be at least {MIN_AUTH_TOKEN} characters")
    elif agent and inbound == agent:
        found.append("QUANTDINGER_MCP_AUTH_TOKEN must differ from QUANTDINGER_AGENT_TOKEN")
    if not public_url.lower().startswith("https://"):
        found.append("QUANTDINGER_MCP_PUBLIC_URL must be the https:// URL of this service")
    if not (env.get("QUANTDINGER_BASE_URL") or "").strip():
        found.append("QUANTDINGER_BASE_URL is empty (the Backend's private URL)")
    return found


def placeholder_handler(reasons: list[str]) -> type:
    body_health = json.dumps({"status": "inactive", "reasons": reasons}).encode()
    body_503 = json.dumps({
        "error": "QuantDinger MCP endpoint is not active yet",
        "reasons": reasons,
        "next_steps": "Set the variables on the MCP Server service in Railway and redeploy it.",
    }).encode()

    class Handler(BaseHTTPRequestHandler):
        server_version = "quantdinger-mcp-placeholder"

        def _send(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _dispatch(self) -> None:
            path = self.path.split("?", 1)[0]
            if self.command in ("GET", "HEAD") and path == HEALTH_PATH:
                self._send(200, body_health)
            else:
                self._send(503, body_503)

        do_GET = do_HEAD = do_POST = do_DELETE = do_OPTIONS = do_PUT = do_PATCH = _dispatch

        def log_message(self, fmt: str, *args) -> None:  # keep Railway logs quiet
            return

    return Handler


def serve_placeholder(env: dict, reasons: list[str]) -> int:
    port = listen_port(env)
    host = (env.get("QUANTDINGER_MCP_HOST") or "0.0.0.0").strip() or "0.0.0.0"
    for reason in reasons:
        log(f"MCP endpoint inactive: {reason}")
    log(f"serving the placeholder on {host}:{port} ({HEALTH_PATH} = 200, everything else = 503)")
    server = ThreadingHTTPServer((host, port), placeholder_handler(reasons))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main() -> int:
    env = dict(os.environ)
    reasons = problems(env)
    if reasons:
        return serve_placeholder(env, reasons)
    env.setdefault("QUANTDINGER_MCP_TRANSPORT", "streamable-http")
    env["QUANTDINGER_MCP_PORT"] = str(listen_port(env))
    env.setdefault("QUANTDINGER_MCP_HOST", "0.0.0.0")
    log(f"starting quantdinger-mcp (streamable HTTP on port {env['QUANTDINGER_MCP_PORT']}, path /mcp)")
    os.execve(sys.executable, [sys.executable, "-m", "quantdinger_mcp.server"], env)
    return 1  # not reached


if __name__ == "__main__":
    sys.exit(main())
