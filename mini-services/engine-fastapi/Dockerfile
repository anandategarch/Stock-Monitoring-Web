# ============================================================
# SM-FastAPI-Engine — Engine PRODUKSI SM-WEB (pipeline v3.9.71, FR-10 0-rewrite).
# Deploy: Railway / Fly.io / Render / VPS (lihat README.md §5.2).
# Port menghormati env PORT (default 3031 — identik dengan mini-service lokal).
# ============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3031

# Pipeline butuh pandas/numpy/calamine — wheel tersedia untuk linux/amd64 & arm64.
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py mapper.py golden_check.py fixtures.py config_template.json ./
COPY src/ ./src/
COPY ports/ ./ports/

EXPOSE 3031
CMD ["sh", "-c", "python -m uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
