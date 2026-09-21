FROM python:3.13-slim-bookworm
USER root
CMD ["sh", "-c", "chown 10001:10001 /runs && chmod 0700 /runs"]
