FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and client code
# We keep them in their respective folders so relative paths in app.py work
COPY backend/ ./backend/
COPY client/ ./client/

# Set working directory to backend to run the app
WORKDIR /app/backend

# Use port 10000 (standard for some cloud providers)
EXPOSE 10000

# The app uses the PORT environment variable if provided
CMD ["python", "app.py"]
