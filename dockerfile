FROM --platform=linux/amd64 python:3.9-slim-buster
RUN apt-get update && apt-get install ffmpeg -y
RUN mkdir /app
ADD . /app
WORKDIR /app
RUN pip install -e .
RUN export FLASK_ENV=production
CMD ["python3", "-m", "videoserver.app"]