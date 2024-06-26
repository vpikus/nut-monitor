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
COPY nut-monitor-api/ ./nut-monitor-api/

RUN <<EOT

cd nut-monitor-api

poetry config virtualenvs.in-project true
poetry install --no-root --no-dev --no-interaction --no-ansi

EOT

FROM python:3.12-alpine

# create non-root user
RUN addgroup -S nonroot && adduser -S nonroot -G nonroot

# configure logging
ENV NUT_API_LOG_DIR /var/log/nut-monitor
RUN mkdir -p $NUT_API_LOG_DIR ; \
    chown -R nonroot:nonroot $NUT_API_LOG_DIR

# configure application home
ENV NUT_API_HOME /app
RUN mkdir -p $NUT_API_HOME; \
    chown -R nonroot:nonroot $NUT_API_HOME

USER nonroot
WORKDIR $NUT_API_HOME

# copy source code
COPY --chown=nonroot:nonroot --from=builder /app/nut-monitor-api/.venv/ .venv/
COPY --chown=nonroot:nonroot --from=builder /app/nut-monitor-api/nut_monitor_api/ .
COPY --chown=nonroot:nonroot nut-monitor-api/config/ config/

# create virtual environment
ENV VIRTUAL_ENV $NUT_API_HOME/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

ENV NUT_API_PORT 8000

# Add a health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:${NUT_API_PORT}/health || exit 1

RUN <<'EOT' cat > run && chmod 0755 run
#!/bin/sh

exec python $VIRTUAL_ENV/bin/gunicorn -c gunicorn.py main:app
"
EOT

CMD ["./run"]
