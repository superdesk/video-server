# HTTP API video editor
Friendly Web HTTP API video editor with pluggable file storages, video editing backends, and streaming capabilities.


## Features
- create a project<sup>[1](#project)</sup>
- list all projects
- retrieve project details
- delete project
- duplicate project
- edit video:
    * trim
    * rotate
    * scale
    * crop
- capture a thumbnails for timeline<sup>[2](#timeline)</sup>
- capture a thumbnail for a preview at a certain position of the video, with optional crop and rotate params
- upload a custom image file for a preview thumbnail
- get thumbnails files
- get video file
- stream video

<a name="project">1</a>: `project` it's a record in db with metadata about video, thumbnails, version, processing statuses, links to files and etc.   
<a name="timeline">2</a>: `timeline` is a display of a list of pictures in chronological order. Useful if you build a UI.


## Installation & Run
These services must be installed, configured and running:

 * Python (>= 3.6)
 * FFmpeg
 * MongoDB 
 * RabbitMQ (celery backend)

After required services were installed and started, 
you can proceed with a video server installation.


### Installation for development
NOTE: Use [virtualenv](https://docs.python.org/3/library/venv.html) and [pip](https://pypi.org/project/pip/) to install python modules.

```
# clone project
git clone https://github.com/superdesk/video-server.git

# install video server for development
# NOTE: your virtualenv must be activated
pip install -e video-server/[dev]
```


### Run video server for development
Video server consists from two main parts: http api and celery workers.  

For starting an http api dev server:
1. Set `FLASK_ENV` env variable to `development`:
```
export FLASK_ENV=development
```
2. Run `python -m videoserver.app`  

For starting a celery workers:
1. Run `celery -A videoserver.worker worker`

### Running tests
NOTE: You can run tests only if project was installed for development!   
There are several options how you can run tests:

1. Run tests directly from your virtualenv.  
Execute `pytest` from video server root.

```
pytest
```

if you want to get a coverage report into your terminal screen 

```
pytest --cov-report term-missing --cov
```

2. Run tests using [tox](https://tox.readthedocs.io/en/latest/).  
It runs tests for each python version specified in `.python-version` file.  
[tox-pyenv](https://pypi.org/project/tox-pyenv/) plugin is used, so python versions from `.python-version` must be installed in yours 
[pyenv](https://github.com/pyenv/pyenv).
Just execute `tox` from  video server root.


### Installation for production
Video server is a module, but not ready to use instance.  
For ready to use installation, please refer to the README file at: https://github.com/superdesk/video-server-app


## Getting Started
Once server is started you can access a swagger via http://0.0.0.0:5050/swagger/ 


## Authors
* **Loi Tran**
* **Oleg Pshenichniy**
* **Petr Jašek**
* **Thanh Nguyen**
