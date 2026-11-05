FROM python:3.12-slim
WORKDIR /app
COPY server.py ./server.py
RUN groupadd --gid 65532 code4fun && useradd --uid 65532 --gid code4fun --create-home code4fun
USER code4fun:code4fun
ENV PYTHONUNBUFFERED=1 USER=code4fun LOGNAME=code4fun
EXPOSE 8092
CMD ["python", "server.py", "--bind", "0.0.0.0"]
