FROM node:24-alpine AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src CYBERMIND_HOME=/state CYBERMIND_CHECKPOINT=/app/checkpoints/final_grouped/best.pt CYBERMIND_WEB_DIST=/app/web/dist CYBERMIND_DEMOS_DIR=/app/examples/analyst_demo
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY examples/analyst_demo/ ./examples/analyst_demo/
COPY checkpoints/final_grouped/best.pt ./checkpoints/final_grouped/best.pt
COPY --from=web /web/dist ./web/dist
RUN useradd --system --create-home cybermind && mkdir /state && chown cybermind:cybermind /state
USER cybermind
EXPOSE 8000
CMD ["python","-m","uvicorn","cybermind.analyst.api:app","--host","0.0.0.0","--port","8000"]

