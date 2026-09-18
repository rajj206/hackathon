FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY demo-data/role-simulations ./demo-data/role-simulations
RUN pip install --no-cache-dir ".[azure]"

RUN useradd --create-home appuser && mkdir -p /data && chown -R appuser:appuser /data
USER appuser

EXPOSE 8000
CMD ["uvicorn", "experttwin.app:app", "--host", "0.0.0.0", "--port", "8000"]
