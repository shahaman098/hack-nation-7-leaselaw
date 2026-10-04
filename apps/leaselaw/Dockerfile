FROM python:3.12-slim
WORKDIR /app
COPY apps/leaselaw/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/leaselaw/ .
COPY briefs/hack-nation-7-realpage-starter/participant-final-no-hour16\ 3 /data/starter
ENV LEASELAW_STARTER=/data/starter
ENV LEASELAW_OFFLINE=1
ENV PORT=8012
EXPOSE 8012
RUN python3 -m src.llm_extract --offline && python3 -m src.export_outputs && python3 -m src.eval_harness
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"
