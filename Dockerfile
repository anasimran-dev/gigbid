# Single-service deployment (Render): web build + API served by one process.
FROM node:20-alpine AS web
WORKDIR /w
COPY apps/web/package*.json ./
RUN npm ci || npm install
COPY apps/web .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
COPY --from=web /w/dist apps/web/dist
ENV MODEL_PROFILE=open GIGBID_SYNC=1 MARKETPLACE_MODE=gigsim APP_DB=data/processed/app.db PYTHONUNBUFFERED=1
CMD ["sh", "-c", "uvicorn apps.api.serve:root --host 0.0.0.0 --port ${PORT:-10000}"]
