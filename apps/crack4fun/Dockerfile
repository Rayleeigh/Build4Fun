FROM python:3.12-slim
WORKDIR /app
COPY apps/crack4fun/workspace ./apps/crack4fun/workspace
COPY challenges/crack ./challenges/crack
RUN groupadd --gid 65532 crack4fun && useradd --uid 65532 --gid crack4fun --create-home crack4fun && mkdir -p /workspace /controls/filesystem /controls/forensics /controls/network-analysis /controls/web-api /controls/portal && chown -R crack4fun:crack4fun /workspace /controls && chmod 700 /controls/*
USER root
ENV PYTHONUNBUFFERED=1
CMD ["python", "apps/crack4fun/workspace/entrypoint.py"]
