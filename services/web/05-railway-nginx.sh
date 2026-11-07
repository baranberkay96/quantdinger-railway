#!/bin/sh
# Runs from the nginx image's /docker-entrypoint.d before 20-envsubst-on-templates.sh.
#
# Upstream's nginx template (QuantDinger-Vue deploy/nginx-docker.conf.template) proxies /api
# through a variable, so nginx re-resolves the Backend name every 10 s, but it hard-codes
# Docker's embedded DNS server (resolver 127.0.0.11 ... ipv6=off), which does not exist on
# Railway. This script rewrites only that resolver line in the nginx config template:
#   - resolver = the container's own DNS server from /etc/resolv.conf (Railway: fd12::10),
#     IPv4 and IPv6 answers, still re-resolved every 10 s, so a Backend redeploy (new
#     private IP) never leaves nginx on a stale address;
#   - trust X-Forwarded-For only from private and loopback addresses (Railway's proxy), so
#     the Backend sees the visitor's IP for its login rate limits instead of the proxy's.
# The web app itself (HTML, JS, branding) is not touched. If the template has no resolver
# line (a future image), nothing is changed and nginx starts with upstream's file.
set -eu

template=/etc/nginx/templates/default.conf.template
if [ ! -f "$template" ]; then
    echo "$0: $template not found; nothing to change" >&2
    exit 0
fi

resolver="${NGINX_RESOLVER:-}"
if [ -z "$resolver" ]; then
    resolver=$(awk '$1 == "nameserver" { print $2; exit }' /etc/resolv.conf 2>/dev/null || true)
fi
if [ -z "$resolver" ]; then
    echo "$0: no nameserver in /etc/resolv.conf and NGINX_RESOLVER is empty; leaving the template unchanged" >&2
    exit 0
fi
case "$resolver" in
    \[*) ;;
    *:*) resolver="[$resolver]" ;;
esac

trust_forwarded="${NGINX_TRUST_FORWARDED_FOR:-true}"
tmp=$(mktemp)
if awk -v resolver="$resolver" -v trust="$trust_forwarded" '
    /^[ \t]*(set_real_ip_from|real_ip_header|real_ip_recursive)[ \t]/ { next }
    /^[ \t]*resolver[ \t]/ && !done {
        print "    resolver " resolver " valid=10s;"
        if (trust == "true") {
            print "    set_real_ip_from 10.0.0.0/8;"
            print "    set_real_ip_from 100.64.0.0/10;"
            print "    set_real_ip_from 172.16.0.0/12;"
            print "    set_real_ip_from 192.168.0.0/16;"
            print "    set_real_ip_from 127.0.0.1;"
            print "    set_real_ip_from fc00::/7;"
            print "    set_real_ip_from ::1;"
            print "    real_ip_header X-Forwarded-For;"
            print "    real_ip_recursive on;"
        }
        done = 1
        next
    }
    { print }
    END { if (!done) exit 3 }
' "$template" > "$tmp"; then
    cat "$tmp" > "$template"
    echo "$0: nginx resolver $resolver, forwarded client IP trusted from private ranges: $trust_forwarded, BACKEND_URL ${BACKEND_URL:-unset}"
else
    echo "$0: no resolver line found in $template; leaving it unchanged" >&2
fi
rm -f "$tmp"
