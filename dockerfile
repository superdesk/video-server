FROM python:3.8-alpine
RUN mkdir /app
ADD . /app
WORKDIR /app
RUN pip install -e .
RUN export FLASK_ENV=development
CMD ["python3", "-m", "videoserver.app"]