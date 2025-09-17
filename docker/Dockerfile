ARG TARGETBASE=ghcr.io/fopina/balances:base-3.9-alpine
FROM ${TARGETBASE}

# split requirements common from other to be able to re-use layers
RUN --mount=type=bind,source=requirements/requirements_common.txt,target=/requirements/requirements_common.txt \
    --mount=type=cache,target=/root/.cache/pip \
    pip install -r /requirements/requirements_common.txt
COPY common /common

ARG ENTRY="anchor"
RUN --mount=type=bind,source=requirements/,target=/requirements/ \
    --mount=type=cache,target=/root/.cache/pip \
    [ ! -e /requirements/requirements_${ENTRY}.txt ] || pip install -r /requirements/requirements_${ENTRY}.txt
COPY ${ENTRY}.py /entry.py
ENV BALANCE_ENTRY="${ENTRY}"

ENTRYPOINT [ "python", "-u", "/entry.py" ]
