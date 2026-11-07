# QuantDinger MCP server (Apache-2.0) for Railway.
#
# Upstream publishes no MCP container image; docker-compose.yml builds mcp_server/ from the
# repository. This build does the same for release v5.8.4: the package's source files are
# downloaded from the release commit (immutable URLs) and checked against SHA-256 values
# recorded when the template was written; dependencies come from PyPI pinned by hash.
# (The PyPI wheel quantdinger-mcp 0.6.2 predates the v5.8.4 source despite the same version
# number, so it is not used.) Base image: the one upstream's mcp_server/Dockerfile pins.
FROM python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5 \
    PYTHONPATH=/opt/quantdinger-mcp

COPY requirements.txt /opt/quantdinger-mcp-requirements.txt
RUN pip install --require-hashes --only-binary=:all: -r /opt/quantdinger-mcp-requirements.txt

# QuantDinger v5.8.4 = commit be718de0034acea548033aa1627529ac62ed0dda (mcp_server/, Apache-2.0).
ADD https://raw.githubusercontent.com/OpenByteInc/QuantDinger/be718de0034acea548033aa1627529ac62ed0dda/mcp_server/src/quantdinger_mcp/__init__.py /opt/quantdinger-mcp/quantdinger_mcp/__init__.py
ADD https://raw.githubusercontent.com/OpenByteInc/QuantDinger/be718de0034acea548033aa1627529ac62ed0dda/mcp_server/src/quantdinger_mcp/server.py /opt/quantdinger-mcp/quantdinger_mcp/server.py
ADD https://raw.githubusercontent.com/OpenByteInc/QuantDinger/be718de0034acea548033aa1627529ac62ed0dda/mcp_server/src/quantdinger_mcp/security.py /opt/quantdinger-mcp/quantdinger_mcp/security.py
ADD https://raw.githubusercontent.com/OpenByteInc/QuantDinger/be718de0034acea548033aa1627529ac62ed0dda/mcp_server/src/quantdinger_mcp/tool_contract.py /opt/quantdinger-mcp/quantdinger_mcp/tool_contract.py
ADD https://raw.githubusercontent.com/OpenByteInc/QuantDinger/be718de0034acea548033aa1627529ac62ed0dda/mcp_server/LICENSE /opt/quantdinger-mcp/LICENSE
# Files added from a URL are 0600; make them readable for the unprivileged runtime user.
RUN cd /opt/quantdinger-mcp \
 && printf '%s\n' \
      "ba564054062d98fd4d047ebd6932fcc58b12d1eaed0a1f429a46cd294e179513  quantdinger_mcp/__init__.py" \
      "3c3cd12d4b108c2793e400f213c98176db6a3ac0881d46da22daa08aef0ecdc7  quantdinger_mcp/server.py" \
      "3665e4ea468ae197237b29c0e0e4b562582d2fbaa8b050d048fd249dd93d3217  quantdinger_mcp/security.py" \
      "9e8983b9deb575a6d46a40bae991159249a3fa76e781f35e630fa6f665ad0d50  quantdinger_mcp/tool_contract.py" \
      "c0a1e0a8cd6a160d060858b2eff80befc9f2cf42db1433d34c1af0f92d6489b0  LICENSE" \
    | sha256sum -c - \
 && chmod 0755 /opt/quantdinger-mcp /opt/quantdinger-mcp/quantdinger_mcp \
 && chmod 0644 /opt/quantdinger-mcp/LICENSE /opt/quantdinger-mcp/quantdinger_mcp/*.py \
 && QUANTDINGER_BASE_URL=http://127.0.0.1:1 QUANTDINGER_AGENT_TOKEN=build-check \
    python -c "import quantdinger_mcp.server as s; assert s.__version__ == '0.6.2', s.__version__; print('quantdinger-mcp', s.__version__, len(s.MCP_TOOL_NAMES), 'tools')" \
 && useradd --uid 10001 --user-group --no-create-home --shell /usr/sbin/nologin quantdinger

# /usr/local/bin exists in the base image (0755).
COPY --chmod=0755 railway_mcp.py /usr/local/bin/railway-mcp

USER 10001
EXPOSE 7800
CMD ["/usr/local/bin/railway-mcp"]
