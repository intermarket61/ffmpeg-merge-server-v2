FROM python:3.9-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y ffmpeg

EXPOSE 80

CMD ["python", "app.py"]
