# QuantDinger backend for Railway: Open Byte Inc.'s published backend image (Apache-2.0),
# unchanged, plus one start/pre-deploy wrapper (railway_quantdinger.py).
#
# Used by Backend and by all eight worker services; each service picks its process with its
# start command (railway-quantdinger api | trading | scheduler | kafka-audit | ...).
# QUANTDINGER_BACKEND_IMAGE is a service variable on Backend (the workers reference it);
# Railway passes service variables to the build as build arguments, so all nine services
# always build from the same pinned image.
ARG QUANTDINGER_BACKEND_IMAGE=ghcr.io/openbyteinc/quantdinger-backend:v5.8.4@sha256:3878e94a1344a979e98b689369ed3fafe51ed065c3d51b11782b7f3dd52d4e26
FROM ${QUANTDINGER_BACKEND_IMAGE}

# /usr/local/bin exists in the base image (0755).
COPY --chmod=0755 railway_quantdinger.py /usr/local/bin/railway-quantdinger

# Fails the build if a future base image no longer has the files and modules the wrapper uses.
RUN /usr/local/bin/railway-quantdinger --self-test

# The wrapper calls upstream's /usr/local/bin/docker-entrypoint.sh itself (SECRET_KEY check,
# volume ownership, drop to the quantdinger user), so the result is the same whether Railway's
# start command replaces the ENTRYPOINT or only the CMD.
ENTRYPOINT []
CMD ["/usr/local/bin/railway-quantdinger", "api"]
