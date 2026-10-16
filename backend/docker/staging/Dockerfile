FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .
RUN chmod +x scripts/*.sh \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /app/static /app/media \
    && chown -R app:app /app

USER app
ENV DJANGO_SETTINGS_MODULE=config.settings.production

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
