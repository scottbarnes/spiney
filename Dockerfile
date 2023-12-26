FROM python:3.10-alpine

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY . /app

EXPOSE 80

CMD ["python3", "main.py"]
