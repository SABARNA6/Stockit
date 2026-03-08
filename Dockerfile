FROM node:18-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm i
COPY frontend/ .
RUN npm run build

# Backend stage
FROM python:3.10-slim
WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY server/ .

# Copy built frontend from previous stage
COPY --from=frontend-build /frontend/dist ./dist

EXPOSE 10000
CMD ["python", "app.py"]
