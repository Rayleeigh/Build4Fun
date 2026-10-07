FROM docker:29-cli AS docker-cli
FROM python:3.12-slim
WORKDIR /app
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src/application ./src/application
COPY src/templates ./src/templates
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "src/application/server.py", "--bind", "0.0.0.0", "--workspace", "/workspace"]
