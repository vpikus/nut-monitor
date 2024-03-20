FROM python:3-alpine

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

# create virtual environment
ENV VIRTUAL_ENV $NUT_API_HOME/venv
RUN pip install --user --no-cache-dir virtualenv ; \
    python -m venv $VIRTUAL_ENV

# install dependencies
COPY --chown=nonroot:nonroot requirements.txt .
RUN source $VIRTUAL_ENV/bin/activate ; \
    pip install --no-cache-dir -r requirements.txt ; \
    pip install --no-cache-dir gunicorn

# copy source code
COPY --chown=nonroot:nonroot src/ .

# configure entrypoint
COPY --chown=nonroot:nonroot --chmod=0755 entrypoint run

ENV NUT_API_PORT 8000
# Add a health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:${NUT_API_PORT}/health || exit 1

CMD ["./run"]
