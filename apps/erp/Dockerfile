FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "fastapi>=0.115,<1.0" "uvicorn[standard]>=0.30,<1.0"
COPY apps/erp ./apps/erp
COPY apps/api/app/security_tokens.py ./apps/api/app/security_tokens.py

ENV PYTHONPATH=/app
ENV ERP_DB_PATH=/data/northstar_erp.db
CMD ["python", "-m", "uvicorn", "apps.erp.server:app", "--host", "0.0.0.0", "--port", "8080"]
