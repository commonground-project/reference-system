FROM python:3.10.11-slim

WORKDIR /app

RUN pip install poetry

RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --no-interaction --no-ansi

COPY src/main_few_shot.py src/
COPY src/utils src/utils
COPY config/.env config/
COPY data/few_shot_example.txt data/

CMD ["python", "src/main_few_shot.py"]