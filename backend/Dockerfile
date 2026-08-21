FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /var/log/app

EXPOSE 8000

# --workers 1 is intentional: login lockout counting and session checks
# read/write Postgres directly (no cache layer), so a single worker keeps
# the request-handling model simple and easy to reason about for the lab.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
