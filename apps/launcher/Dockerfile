FROM docker:29-cli AS docker-cli
FROM python:3.12-slim
WORKDIR /app
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
COPY apps/launcher/ ./
ENV PYTHONUNBUFFERED=1 LAUNCHER_STATE=/state
EXPOSE 8070
CMD ["python", "server.py", "--bind", "0.0.0.0"]
