FROM docker:29-cli AS docker-cli
FROM python:3.12-slim
WORKDIR /app
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
COPY apps/build4fun/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/build4fun/application ./apps/build4fun/application
COPY apps/build4fun/templates ./apps/build4fun/templates
COPY challenges/build ./challenges/build
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "apps/build4fun/application/server.py", "--bind", "0.0.0.0", "--workspace", "/workspace"]
