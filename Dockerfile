FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 cred \
    && useradd --uid 10001 --gid cred --no-create-home cred \
    && mkdir /data \
    && chown cred:cred /data
COPY app.py monitor.py /app/
COPY --chown=cred:cred fixtures/message.txt /data/message.txt
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=2s --timeout=2s --start-period=3s --retries=2 \
    CMD ["python", "monitor.py", "--once"]
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "8080", "--message-file", "/data/message.txt"]
