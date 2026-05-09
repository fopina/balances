ARG TARGETBASE=ghcr.io/fopina/balances:base-3.9-alpine
FROM ${TARGETBASE}

COPY common /common

ARG ENTRY="anchor"
ARG ENTRY_FILE="${ENTRY}/main.py"
RUN --mount=type=bind,source=${ENTRY}/requirements.txt,target=/entry/requirements.txt \
    --mount=type=bind,source=libs,target=/libs \
    --mount=type=cache,target=/root/.cache/pip \
    mkdir -p /tmp/entry /tmp/libs && \
    cp /entry/requirements.txt /tmp/entry/requirements.txt && \
    cp -a /libs/. /tmp/libs/ && \
    cd /tmp/entry && \
    pip install -r requirements.txt
COPY ${ENTRY_FILE} /entry.py
ENV BALANCE_ENTRY="${ENTRY}"

ENTRYPOINT [ "python", "-u", "/entry.py" ]
