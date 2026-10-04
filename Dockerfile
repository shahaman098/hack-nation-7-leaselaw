# Repo-root entry for Render (dockerContext: .). Same as apps/leaselaw/Dockerfile.
FROM python:3.12-slim
WORKDIR /app
COPY apps/leaselaw/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/leaselaw/ .
COPY apps/leaselaw/deploy/starter-pack /data/starter
ENV LEASELAW_STARTER=/data/starter
ENV LEASELAW_OFFLINE=1
ENV PORT=8012
EXPOSE 8012
RUN python3 -m src.eval_harness
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8012}"
