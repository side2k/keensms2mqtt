FROM python:3.11-slim AS poetry


RUN apt update && \
    apt upgrade && \
    apt install -y curl

ENV PYTHONUNBUFFERED=1
ENV POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_HOME="/opt/poetry" \
    PYSETUP_PATH="/opt/python-deps" \
    VENV_PATH="/opt/python-deps/.venv"

ENV PATH="${POETRY_HOME}/bin:${VENV_PATH}/bin:${PATH}"

RUN curl -sSL https://install.python-poetry.org -o poetry-installer.py
RUN python3 poetry-installer.py

WORKDIR ${PYSETUP_PATH}
COPY pyproject.toml .
COPY poetry.lock .

RUN poetry install --only main

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYSETUP_PATH="/opt/python-deps"
ENV VENV_PATH="${PYSETUP_PATH}/.venv"
ENV PATH="${VENV_PATH}/bin:${PATH}"
ENV PYTHONPYCACHEPREFIX=/app/__pycache__.docker

COPY --from=poetry $PYSETUP_PATH $PYSETUP_PATH

RUN mkdir /app/
WORKDIR /app

COPY . .

CMD ["bash", "entrypoint.sh"]
