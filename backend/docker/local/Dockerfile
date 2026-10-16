FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/development.txt

COPY . .
RUN chmod +x scripts/*.sh

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
