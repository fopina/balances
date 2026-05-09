ARG TARGETBASE=ghcr.io/fopina/balances:base-3.9-alpine
FROM ${TARGETBASE}

COPY common /common

ARG ENTRY="anchor"
ARG ENTRY_FILE="${ENTRY}.py"
ARG ENTRY_PACKAGE_REQUIREMENTS="requirements/requirements_common.txt"
ARG INSTALL_ENTRY_PACKAGE_REQUIREMENTS="0"
RUN --mount=type=bind,source=${ENTRY_PACKAGE_REQUIREMENTS},target=/entry/requirements.txt \
    --mount=type=bind,source=libs,target=/libs \
    --mount=type=cache,target=/root/.cache/pip \
    if [ "${INSTALL_ENTRY_PACKAGE_REQUIREMENTS}" = "1" ]; then \
        mkdir -p /tmp/entry /tmp/libs && \
        cp /entry/requirements.txt /tmp/entry/requirements.txt && \
        cp -a /libs/. /tmp/libs/ && \
        cd /tmp/entry && \
        pip install -r requirements.txt; \
    fi
COPY ${ENTRY_FILE} /entry.py
ENV BALANCE_ENTRY="${ENTRY}"

ENTRYPOINT [ "python", "-u", "/entry.py" ]
