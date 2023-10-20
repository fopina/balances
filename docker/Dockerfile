ARG TARGETBASE=3.9-alpine
FROM ghcr.io/fopina/balances:base-${TARGETBASE}

ARG ENTRY="anchor"
COPY requirements/requirements_common.txt /requirements_common.txt
COPY requirements/requirements_${ENTRY}.txt /requirements.txt
RUN pip install -r /requirements_common.txt -r /requirements.txt
COPY common /common
COPY ${ENTRY}.py /entry.py

ENTRYPOINT [ "python", "-u", "/entry.py" ]
