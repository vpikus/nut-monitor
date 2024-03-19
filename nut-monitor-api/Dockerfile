FROM python:3-alpine

ENV NUT_API_HOME /app
WORKDIR $NUT_API_HOME

# install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt ; \
    pip install --no-cache-dir gunicorn

# copy source code
COPY src/ .

# configure logging
ENV NUT_API_LOG_DIR /var/log/nut-monitor
RUN mkdir -p $NUT_API_LOG_DIR

# configure entrypoint
COPY --chown=root:root --chmod=0755 entrypoint run

CMD ["./run"]
