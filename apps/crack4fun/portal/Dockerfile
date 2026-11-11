FROM python:3.12-slim
WORKDIR /app
COPY apps/crack4fun/portal/server.py ./server.py
RUN groupadd --gid 65532 crack4fun && useradd --uid 65532 --gid crack4fun --create-home crack4fun && mkdir /state && chown crack4fun:crack4fun /state
USER crack4fun:crack4fun
ENV PYTHONUNBUFFERED=1
CMD ["python", "server.py"]
