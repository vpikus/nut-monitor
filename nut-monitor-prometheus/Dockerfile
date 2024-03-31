FROM python:3.12-alpine as builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies required for compiling cffi
# gcc, musl-dev, and libffi-dev are typically required
RUN apk add --no-cache gcc musl-dev libffi-dev

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade pip setuptools wheel

RUN pip install poetry

WORKDIR /app

COPY nut-monitor-client/ ./nut-monitor-client/
COPY nut-monitor-prometheus/ ./nut-monitor-prometheus/

RUN <<EOT

cd nut-monitor-prometheus

poetry config virtualenvs.in-project true
poetry install --no-root --no-dev --no-interaction --no-ansi

EOT

FROM python:3.12-alpine

# create non-root user
RUN addgroup -S nonroot && adduser -S nonroot -G nonroot

# configure logging
ENV NUT_PROMETEUS_LOG_DIR /var/log/nut-monitor
RUN mkdir -p $NUT_PROMETEUS_LOG_DIR ; \
    chown -R nonroot:nonroot $NUT_PROMETEUS_LOG_DIR

# configure application home
ENV NUT_PROMETEUS_HOME /app
RUN mkdir -p $NUT_PROMETEUS_HOME; \
    chown -R nonroot:nonroot $NUT_PROMETEUS_HOME

USER nonroot
WORKDIR $NUT_PROMETEUS_HOME

# copy source code
COPY --chown=nonroot:nonroot --from=builder /app/nut-monitor-prometheus/.venv/ .venv/
COPY --chown=nonroot:nonroot --from=builder /app/nut-monitor-prometheus/nut_monitor_prometheus/ .
COPY --chown=nonroot:nonroot nut-monitor-prometheus/config/ config/

# create virtual environment
ENV VIRTUAL_ENV $NUT_PROMETEUS_HOME/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV NUT_PROMETEUS_PORT 8000

# Add a health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:${NUT_PROMETEUS_PORT}/metrics || exit 1

RUN <<'EOT' cat > run && chmod 0755 run
#!/bin/sh

exec python ./prometeus.py
"
EOT

CMD ["./run"]
