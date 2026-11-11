FROM python:3.12-slim
WORKDIR /app
COPY apps/code4fun/workspace/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers PYTHONUNBUFFERED=1 HOME=/tmp
RUN python -m playwright install --with-deps chromium && chmod -R a+rX /opt/browsers
COPY apps/code4fun/workspace ./apps/code4fun/workspace
COPY challenges/code ./challenges/code
RUN groupadd --gid 65532 code4fun && useradd --uid 65532 --gid code4fun --create-home code4fun \
    && mkdir /workspace && chown code4fun:code4fun /workspace
USER code4fun:code4fun
EXPOSE 8090 8091
CMD ["python", "apps/code4fun/workspace/server.py", "--bind", "0.0.0.0", "--workspace", "/workspace"]
