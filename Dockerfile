FROM python:3.10.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/main_few_shot.py src/
COPY config/.env config/
COPY data/example_api_data.json data/
COPY data/few_shot_example.txt data/

CMD ["python","src/main_few_shot.py"]