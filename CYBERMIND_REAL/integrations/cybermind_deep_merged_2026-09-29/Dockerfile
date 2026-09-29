FROM node:24-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM docker:cli AS docker_cli

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src CYBERMIND_DEVICE=cpu
WORKDIR /app
COPY requirements-runtime.txt ./
RUN pip install --no-cache-dir 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements-runtime.txt
COPY --from=docker_cli /usr/local/bin/docker /usr/local/bin/docker
RUN docker --version
COPY app/ ./app/
COPY sandbox/ ./sandbox/
COPY src/ ./src/
COPY knowledge/stage_mapping.yaml ./knowledge/stage_mapping.yaml
COPY models/best.pt ./models/best.pt
COPY results/final_grouped_model_comparison.json ./results/final_grouped_model_comparison.json
COPY data/test_cases/ ./data/test_cases/
COPY examples/test_cases/ ./examples/test_cases/
COPY tools/incident_decrypter/index.html ./tools/incident_decrypter/index.html
COPY --from=frontend /build/frontend/dist ./frontend/dist
RUN mkdir -p data/replay data/test_cases data/runs data/strix_runs
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
