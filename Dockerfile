# One image for hosts like Render: builds the React app, then serves it and the API from Django.
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY --from=frontend /app/dist ./frontend_dist
RUN chmod +x start.sh
CMD ["./start.sh"]
