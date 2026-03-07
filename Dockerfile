FROM python:3.12-slim

ENV SCAD_BINARY=openscad DEBUG=False PORT=8000

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends git gcc openscad && \
    rm -rf /var/lib/apt/lists/*

RUN pip install poetry

ENV APP_HOME=/app
WORKDIR $APP_HOME
COPY . .

RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --without dev --extras service

RUN python manage.py collectstatic --noinput

RUN useradd --no-create-home appuser && chown -R appuser $APP_HOME
USER appuser

CMD gunicorn gts_service.wsgi --bind :$PORT --workers 1 --threads 8
