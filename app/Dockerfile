FROM python:3.9.0

ARG PROD_ENV=production
ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.2.0

RUN apt-get update -y && apt-get install ffmpeg -y

RUN apt-get clean -y && rm -rf /var/lib/apt/lists/*

# install poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/etc/poetry python3 - && \
    cd /usr/local/bin && \
    ln -s /etc/poetry/bin/poetry && \
    poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry install $(if [ "$PROD_ENV" = "production" ]; then echo --only main; fi) --no-interaction --no-ansi

RUN poe install_lap

COPY app /app

ENTRYPOINT [ "/bin/bash" , "-c"]