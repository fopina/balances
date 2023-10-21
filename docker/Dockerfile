ARG TARGETBASE=ghcr.io/fopina/balances:base-3.9-alpine
FROM ${TARGETBASE}

ARG ENTRY="anchor"
RUN --mount=type=bind,source=requirements/,target=/requirements/ \
    --mount=type=cache,target=/root/.cache/pip \
    pip install -r /requirements/requirements_common.txt \
 && ([ ! -e /requirements/requirements_${ENTRY}.txt ] || pip install -r /requirements/requirements_${ENTRY}.txt)

COPY common /common
COPY ${ENTRY}.py /entry.py

ENTRYPOINT [ "python", "-u", "/entry.py" ]
