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


### Endpoints

##### List all projects
```bash
curl -X GET http://0.0.0.0:5050/projects/
```

##### Create a project
```bash
curl -X POST http://0.0.0.0:5050/projects/ \
  -F file=@/path/to/your/video/SampleVideo.mp4
```

##### Retrieve project details
```bash
curl -X GET http://0.0.0.0:5050/projects/5d7b841764c598157d53ef4a
```
where `5d7b841764c598157d53ef4a` is project's `_id`.

##### Delete a project
```bash
curl -X DELETE http://0.0.0.0:5050/projects/5d7b841764c598157d53ef4a
```
where `5d7b841764c598157d53ef4a` is project's `_id`.


##### Duplicate a project
```bash
curl -X POST http://0.0.0.0:5050/projects/5d7b841764c598157d53ef4a/duplicate
```
where `5d7b841764c598157d53ef4a` is project's `_id` you want to make a duplicate of.

##### Edit

:warning: It's not permitted to edit an original project (version 1), instead use a duplicated project.

##### Trim
```bash
curl -X PUT \
  http://0.0.0.0:5050/projects/5d7a35a04be797ba845e7871 \
  -d '{
	"trim": "2,5"
}'
```
where `2` and `5` are seconds.

##### Rotate
```bash
curl -X PUT \
  http://0.0.0.0:5050/projects/5d7a35a04be797ba845e7871 \
  -d '{
	"rotate": 90
}'
```
where `90` is rotate degree.

##### Scale
```bash
curl -X PUT \
  http://0.0.0.0:5050/projects/5d7a35a04be797ba845e7871 \
  -d '{
	"scale": 480
}'
```
where `480` is width you want to scale video to.

##### Crop
```bash
curl -X PUT \
  http://0.0.0.0:5050/projects/5d7a35a04be797ba845e7871 \
  -d '{
	"crop": "0,0,180,320"
}'
```
where `width` and `height` are respectively width and height of capturing area,
and `x` and `y` are coordinates of top-left point of capturing area.
https://ffmpeg.org/ffmpeg-filters.html#crop

##### Capture timeline thumbnails
```bash
curl -X GET 'http://0.0.0.0:5050/projects/5d7b90ed64c598157d53ef5d/thumbnails?type=timeline&amount=5'
```

##### Capture a thumbnail for a preview at a certain position
```bash
curl -X GET 'http://0.0.0.0:5050/projects/5d7b98f52fac91d2e1ad7512/thumbnails?type=preview&position=5'
```
where `position` is a position in the video (seconds) used to capture a thumbnail. 

You can also specify optional `crop` param if you want to crop a preview thumbnail, just add
`crop="0,0,180,320"`.
Example:
```bash
curl -X GET \
  'http://0.0.0.0:5050/projects/5d7b98f52fac91d2e1ad7512/thumbnails?type=preview&position=5&crop={%0A%09%09%22height%22:%20180,%0A%09%09%22width%22:%20320,%0A%09%09%22x%22:%200,%0A%09%09%22y%22:%200%0A%09}'
```

##### Upload a custom image file for a preview thumbnail
```bash
curl -X POST \
  http://0.0.0.0:5050/projects/5d7b98f52fac91d2e1ad7512/thumbnails \
  -F file=@/path/to/your/video/tom_and_jerry.jpg
```

##### Get timeline thumbnail file
```bash
curl -X GET http://0.0.0.0:5050/projects/5d7b98f52fac91d2e1ad7512/raw/thumbnails/timeline/3
```
where `3` is a thumbnail index

##### Get preview thumbnail file
```bash
curl -X GET http://0.0.0.0:5050/projects/5d7b98f52fac91d2e1ad7512/raw/thumbnails/preview
```

##### Get video file
```bash
curl -X GET http://0.0.0.0:5050/projects/5d7b98f52fac91d2e1ad7512/raw/video 
```
NOTE: If `HTTP_RANGE` header is specified - chunked video will be streamed, else full file.


## Authors
* **Loi Tran**
* **Oleg Pshenichniy**
* **Petr Jašek**
* **Thanh Nguyen**
