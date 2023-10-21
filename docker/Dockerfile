ARG TARGETBASE=ghcr.io/fopina/balances:base-3.9-alpine
FROM ${TARGETBASE}

ARG ENTRY="anchor"
RUN --mount=type=bind,source=requirements/requirements_common.txt,target=/requirements/requirements_common.txt \
    --mount=type=bind,source=requirements/requirements_${ENTRY}.txt,target=/requirements/requirements.txt \
    --mount=type=cache,target=/root/.cache/pip \
    pip install -r /requirements/requirements_common.txt \
                -r /requirements/requirements.txt
COPY common /common
COPY ${ENTRY}.py /entry.py

ENTRYPOINT [ "python", "-u", "/entry.py" ]
