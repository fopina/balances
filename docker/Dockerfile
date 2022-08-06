ARG BASE=python:3.9-alpine
ARG BASESLIM=python:3.9-slim
ARG TARGETBASE=alpine

# ==== ALPINE BASE ====
FROM ${BASE} as alpine

ARG ENTRY="anchor"
COPY requirements/requirements_common.txt /requirements_common.txt
COPY requirements/requirements_${ENTRY}.txt /requirements.txt
RUN pip install -r /requirements_common.txt -r /requirements.txt
COPY common /common
COPY ${ENTRY}.py /entry.py

ENTRYPOINT [ "python", "-u", "/entry.py" ]
# =====================

# === SLIM+GCC BASE ===
FROM ${BASESLIM} as gcc

# FIXME use wheels and multistage to reduce size
RUN apt update \
 && apt install --no-install-recommends -y \
    build-essential \
 && rm -rf /var/lib/apt/lists/*
# =====================

# === CHROMIUM BASE ===
# Chrome dockerfile based on https://github.com/justinribeiro/dockerfiles/blob/master/chrome-headless/Dockerfile
FROM ${BASESLIM} as baseslim-armv7
ADD docker/pip.conf.armv7 /etc/pip.conf

FROM ${BASESLIM} as baseslim-arm64
FROM ${BASESLIM} as baseslim-amd64

FROM baseslim-${TARGETARCH}${TARGETVARIANT} as chromium

# FIXME use wheels and multistage to reduce size
RUN apt update \
 && apt install --no-install-recommends -y \
    chromium-driver \
    #build-essential \
    # because there is no cffi wheel for armv7...
    #libffi-dev \
 && rm -rf /var/lib/apt/lists/*

FROM ${TARGETBASE}

ARG ENTRY="anchor"
COPY requirements/requirements_common.txt /requirements_common.txt
COPY requirements/requirements_${ENTRY}.txt /requirements.txt
RUN pip install -r /requirements_common.txt -r /requirements.txt
COPY common /common
COPY ${ENTRY}.py /entry.py

ENTRYPOINT [ "python", "-u", "/entry.py" ]
