# Foresight — single-image deploy: build the SPA, then serve it + the API from
# one FastAPI process (same origin, so the websocket + /api just work).

# ---- stage 1: build the frontend ----
FROM node:20-slim AS web
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- stage 2: python runtime ----
FROM python:3.12-slim
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# the built SPA goes where main.py looks for it (C.ROOT/frontend/dist)
COPY --from=web /app/frontend/dist /app/frontend/dist
EXPOSE 8011
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8011}"]
