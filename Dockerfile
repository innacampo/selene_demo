FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

# Ensure selene package is always importable (belt-and-suspenders)
ENV PYTHONPATH="/app/src"

# Copy application code and static assets
COPY app.py ./
COPY .streamlit/ ./.streamlit/
COPY data/metadata/ ./data/metadata/

# Create writable directories for runtime data
RUN mkdir -p data/user_data/backups data/user_data/user_med_db data/reports data/output

EXPOSE 7860

HEALTHCHECK CMD curl --fail http://localhost:7860/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]