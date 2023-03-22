# base ubuntu 20.04 image
FROM ubuntu:focal

## system-wide dependencies
## system-wide dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential git ffmpeg bc \
    python3 python3-dev python3-pip python3-setuptools python3-wheel

# install video-server app
WORKDIR /opt/video-server-app
COPY ./ /opt/video-server-app
RUN pip3 install -r requirements.txt
RUN pip3 install -e .
# RUN export FLASK_ENV=production

# run
ENTRYPOINT ["honcho"]
CMD ["start"]