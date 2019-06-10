# Superdesk Video Server
_Apr 2019,   
[![Build Status](https://travis-ci.org/superdesk/video-server.svg?branch=master)](https://travis-ci.org/superdesk/video-server)
[![Coverage Status](https://coveralls.io/repos/github/superdesk/video-server/badge.svg?branch=master)](https://coveralls.io/github/superdesk/video-server?branch=master)

## Overview
This is a server for process video for [superdesk](https://github.com/superdesk/video-server).  
It allows to edit video such as cut, crop, rotate, quality and capture thumbnails for video. 

## Configure Superdesk
You only configure it in server and run it as stand alone service.

### Requirements

These services must be installed, configured and running:

 * MongoDB 
 * Python (>= 3.6)
 * RabbitMQ
 * Ffmpeg

## Install for Development

First you will need to clone the repo from GitHub.  
In the root folder where your current superdesk folder is, run the following:
```
git clone git@github.com:superdesk/video-server.git

pip3 install -r requirement.txt

honcho start
```

## Run Tests

simple run with py.test
```
cd video-server
pytest
```

