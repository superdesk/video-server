# HTTP API video editor

Friendly HTTP API video editor with pluggable file storage, video editing backend, and streaming capabilities.

[![Build Status](https://travis-ci.org/superdesk/video-server.svg?branch=master)](https://travis-ci.org/superdesk/video-server)
[![Coverage Status](https://coveralls.io/repos/github/superdesk/video-server/badge.svg?branch=master)](https://coveralls.io/github/superdesk/video-server?branch=master)

## Main features
- upload video
- edit video:
    * trim
    * rotate
    * scale
    * crop
- manage video projects:
    * retrieve
    * list
    * create
    * duplicate
    * delete
- capture and save thumbnails for preview and timeline
- upload custom thumbnail for preview
- get thumbnails
- stream video

### Installing

These services must be installed, configured and running:

 * Python (>= 3.6)
 * FFmpeg
 * MongoDB 
 * RabbitMQ (celery backend)

After required services were installed and running, 
you will need to clone the repo and install python dependencies:

NOTE: use [virtualenv](https://docs.python.org/3/library/venv.html) and [pip](https://pypi.org/project/pip/) to install python modules.

```
# clone project
git clone git@github.com:superdesk/video-server.git

# install python dependencies
pip3 install -r requirement.txt

# run gunicorn process for http api and celery for delayed jobs
honcho start
```


## Running the tests

Just run from the project's root:

```
pytest
```

or 

```
pytest --cov-report term-missing --cov
```
if you want to get a coverage report into your terminal screen

## Getting Started

Once server is started you can access a swagger via http://0.0.0.0:5050/swagger/ 


## Authors

* **Loi Tran**
* **Oleg Pshenichniy**
* **Petr Jašek**
* **Thanh Nguyen**
