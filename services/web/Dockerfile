# QuantDinger web UI for Railway: Open Byte Inc.'s published frontend image, unmodified
# (QuantDinger Frontend Source-Available License, see NOTICE.md; the app, its branding and
# "Powered by QuantDinger" notices are not touched).
#
# One file is added: an nginx entrypoint hook that replaces the Docker-only DNS resolver in
# the image's nginx config template with the container's resolver (Railway private DNS).
# QUANTDINGER_FRONTEND_IMAGE is a service variable; Railway passes it as a build argument.
ARG QUANTDINGER_FRONTEND_IMAGE=ghcr.io/openbyteinc/quantdinger-frontend:5.8.4@sha256:fc993eb1eef5152097e95db8969691692b7c02272055fc801e2c603761c09b8d
FROM ${QUANTDINGER_FRONTEND_IMAGE}

# /docker-entrypoint.d exists in the nginx base image (0755); scripts run in name order,
# so 05-* runs before 20-envsubst-on-templates.sh renders the template.
COPY --chmod=0755 05-railway-nginx.sh /docker-entrypoint.d/05-railway-nginx.sh
