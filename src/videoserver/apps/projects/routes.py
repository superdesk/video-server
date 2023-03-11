import copy
import logging
import os
import re
from datetime import datetime

import bson
from flask import current_app as app
from flask import request
from pymongo import ReturnDocument
from pymongo.errors import ServerSelectionTimeoutError
from werkzeug.exceptions import BadRequest, Conflict, InternalServerError, NotFound

from videoserver.lib.video_editor import get_video_editor
from videoserver.lib.views import MethodView
from videoserver.lib.utils import (
    add_urls, create_file_name, get_request_address, json_response, paginate, save_activity_log, storage2response,
    validate_document
)

from . import bp
from .tasks import edit_video, generate_preview_thumbnail, generate_timeline_thumbnails

logger = logging.getLogger(__name__)


class ListUploadProject(MethodView):
    SCHEMA_UPLOAD = {
        'file': {
            'type': 'filestorage',
            'required': True
        }
    }

    def post(self):
        """
        Upload video file and create new project for it
        ---
        consumes:
          - multipart/form-data
        parameters:
        - in: formData
          name: file
          type: file
          description: video file to upload
        responses:
          201:
            description: Created project details
            schema:
                type: object
                properties:
                  _id:
                    type: string
                    example: 5cbd5acfe24f6045607e51aa
                  filename:
                    type: string
                    example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                  storage_id:
                    type: string
                    example: 2019/7/2/5cbd5acfe24f6045607e51aa/9c8e970807104c848afceea44fa07d1a.mp4
                  metadata:
                    type: object
                    properties:
                      codec_name:
                        type: string
                        example: h264
                      codec_long_name:
                        type: string
                        example: H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
                      width:
                        type: int
                        example: 640
                      height:
                        type: int
                        example: 360
                      duration:
                        type: float
                        example: 300.014000
                      bit_rate:
                        type: int
                        example: 287654
                      nb_frames:
                        type: int
                        example: 7654
                      r_frame_rate:
                        type: string
                        example: 24/1
                      format_name:
                        type: string
                        example: mov,mp4,m4a,3gp,3g2,mj2
                      size:
                        type: int
                        example: 14567890
                  url:
                    type: string
                    example: http://localhost:5050/projects/5cbd5acfe24f6045607e51aa/raw/video
                  mime_type:
                    type: string
                    example: video/mp4
                  create_time:
                    type: string
                    example: 2019-07-02T15:02:32+00:00
                  original_filename:
                    type: string
                    example: video.mp4
                  request_address:
                    type: string
                    example: 127.0.0.1
                  version:
                    type: integer
                    example: 1
                  parent:
                    type: string
                    example: 5d2c8078fe985e7587b50de7
                  processing:
                    type: object
                    properties:
                      video:
                        type: boolean
                        example: False
                      thumbnail_preview:
                        type: boolean
                        example: False
                      thumbnails_timeline:
                        type: boolean
                        example: False
                  thumbnails:
                    type: object
                    properties:
                      timeline:
                        type: array
                        example: []
                      preview:
                        type: object
                        example: {}
        """

        # validate request
        if 'file' not in request.files:
            # to avoid TypeError: cannot serialize '_io.BufferedRandom' error
            raise BadRequest({"file": ["required field"]})
        document = validate_document(request.files, self.SCHEMA_UPLOAD)

        # validate codec
        file_stream = document['file'].stream.read()
        metadata = get_video_editor().get_meta(file_stream)
        if metadata.get('codec_name') not in app.config.get('CODEC_SUPPORT_VIDEO'):
            raise BadRequest({'file': [f"Codec: '{metadata.get('codec_name')}' is not supported."]})

        # add record to database
        project = {
            '_id': bson.ObjectId(),
            'filename': create_file_name(ext=document['file'].filename.rsplit('.')[-1]),
            'storage_id': None,
            'metadata': metadata,
            'create_time': datetime.utcnow(),
            'mime_type': document['file'].mimetype,
            'request_address': get_request_address(request.headers.environ),
            'original_filename': document['file'].filename,
            'version': 1,
            'parent': None,
            'processing': {
                'video': False,
                'thumbnail_preview': False,
                'thumbnails_timeline': False
            },
            'thumbnails': {
                'timeline': [],
                'preview': {},
            }
        }

        # put file stream into storage
        storage_id = app.fs.put(
            content=file_stream,
            filename=project['filename'],
            project_id=project['_id'],
            content_type=document['file'].mimetype
        )
        # set 'storage_id' for project
        project['storage_id'] = storage_id

        try:
            # save project
            app.mongo.db.projects.insert_one(project)
        except ServerSelectionTimeoutError as e:
            # delete project dir
            app.fs.delete_dir(storage_id)
            raise InternalServerError(str(e))

        logger.info(f"New project was created. ID: {project['_id']}")
        save_activity_log('UPLOAD', project['_id'], project)
        add_urls(project)

        return json_response(project, status=201)

    def get(self):
        """
        List of projects
        ---
        parameters:
        - name: page
          in: query
          type: integer
          description: Page number
        responses:
          200:
            description: list of projects
            schema:
              type: object
              properties:
                _meta:
                  type: object
                  properties:
                    page:
                      type: integer
                      example: 1
                    max_results:
                      type: integer
                      example: 25
                    total:
                      type: integer
                      example: 230
                _items:
                  type: array
                  items:
                    type: object
                    properties:
                      _id:
                        type: string
                        example: 5cbd5acfe24f6045607e51aa
                      filename:
                        type: string
                        example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                      storage_id:
                        type: string
                        example: 2019/7/2/5cbd5acfe24f6045607e51aa/9c8e970807104c848afceea44fa07d1a.mp4
                      metadata:
                        type: object
                        properties:
                          codec_name:
                            type: string
                            example: h264
                          codec_long_name:
                            type: string
                            example: H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
                          width:
                            type: int
                            example: 640
                          height:
                            type: int
                            example: 360
                          duration:
                            type: float
                            example: 300.014000
                          bit_rate:
                            type: int
                            example: 287654
                          nb_frames:
                            type: int
                            example: 7654
                          r_frame_rate:
                            type: string
                            example: 24/1
                          format_name:
                            type: string
                            example: mov,mp4,m4a,3gp,3g2,mj2
                          size:
                            type: int
                            example: 14567890
                      url:
                        type: string
                        example: http://localhost:5050/projects/5cbd5acfe24f6045607e51aa/raw/video
                      mime_type:
                        type: string
                        example: video/mp4
                      create_time:
                        type: string
                        example: 2019-07-02T15:02:32+00:00
                      original_filename:
                        type: string
                        example: video.mp4
                      request_address:
                        type: string
                        example: 127.0.0.1
                      version:
                        type: integer
                        example: 1
                      parent:
                        type: string
                        example: 5d2c8078fe985e7587b50de7
                      processing:
                        type: object
                        properties:
                          video:
                            type: boolean
                            example: False
                          thumbnail_preview:
                            type: boolean
                            example: False
                          thumbnails_timeline:
                            type: boolean
                            example: False
                      thumbnails:
                        type: object
                        properties:
                          timeline:
                            type: array
                            example: []
                          preview:
                            type: object
                            example: {}
        """

        page = request.args.get('page', 1, type=int)
        projects = list(paginate(
            cursor=app.mongo.db.projects.find(),
            page=page
        ))
        add_urls(projects)

        return json_response(
            {
                '_items': projects,
                '_meta': {
                    'page': page,
                    'max_results': app.config.get('ITEMS_PER_PAGE'),
                    'total': app.mongo.db.projects.estimated_document_count()
                }
            }
        )


class RetrieveEditDestroyProject(MethodView):

    @property
    def schema_edit(self):
        return {
            'trim': {
                'required': False,
                'regex': r'^\d+\.?\d*,\d+\.?\d*$',
                'coerce': 'trim_to_dict',
                'min_trim_start': 0,
                'min_trim_end': 1
            },
            'rotate': {
                'type': 'integer',
                'required': False,
                'allowed': [-270, -180, -90, 90, 180, 270]
            },
            'scale': {
                'type': 'integer',
                'min': app.config.get('MIN_VIDEO_WIDTH'),
                'max': app.config.get('MAX_VIDEO_WIDTH'),
                'required': False
            },
            'crop': {
                'required': False,
                'regex': r'^\d+,\d+,\d+,\d+$',
                'coerce': 'crop_to_dict',
                'allow_crop_width': [app.config.get('MIN_VIDEO_WIDTH'), app.config.get('MAX_VIDEO_WIDTH')],
                'allow_crop_height': [app.config.get('MIN_VIDEO_HEIGHT'), app.config.get('MAX_VIDEO_HEIGHT')]
            }
        }

    def get(self, project_id):
        """
        Retrieve project details
        ---
        parameters:
            - name: project_id
              in: path
              type: string
              required: true
              description: Unique project id
        responses:
          200:
            description: Project details
            schema:
                type: object
                properties:
                  _id:
                    type: string
                    example: 5cbd5acfe24f6045607e51aa
                  filename:
                    type: string
                    example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                  storage_id:
                    type: string
                    example: 2019/7/2/5cbd5acfe24f6045607e51aa/9c8e970807104c848afceea44fa07d1a.mp4
                  metadata:
                    type: object
                    properties:
                      codec_name:
                        type: string
                        example: h264
                      codec_long_name:
                        type: string
                        example: H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
                      width:
                        type: int
                        example: 640
                      height:
                        type: int
                        example: 360
                      duration:
                        type: float
                        example: 300.014000
                      bit_rate:
                        type: int
                        example: 287654
                      nb_frames:
                        type: int
                        example: 7654
                      r_frame_rate:
                        type: string
                        example: 24/1
                      format_name:
                        type: string
                        example: mov,mp4,m4a,3gp,3g2,mj2
                      size:
                        type: int
                        example: 14567890
                  url:
                    type: string
                    example: http://localhost:5050/projects/5cbd5acfe24f6045607e51aa/raw/video
                  mime_type:
                    type: string
                    example: video/mp4
                  create_time:
                    type: string
                    example: 2019-07-02T15:02:32+00:00
                  original_filename:
                    type: string
                    example: video.mp4
                  request_address:
                    type: string
                    example: 127.0.0.1
                  version:
                    type: integer
                    example: 1
                  parent:
                    type: string
                    example: 5d2c8078fe985e7587b50de7
                  processing:
                    type: object
                    properties:
                      video:
                        type: boolean
                        example: False
                      thumbnail_preview:
                        type: boolean
                        example: False
                      thumbnails_timeline:
                        type: boolean
                        example: False
                  thumbnails:
                    type: object
                    properties:
                      timeline:
                        type: array
                        example: []
                      preview:
                        type: object
                        example: {}
        """

        add_urls(self.project)
        return json_response(self.project)

    def put(self, project_id):
        """
        Edit project's video
        ---
        consumes:
        - application/json
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
          description: Unique project id
        - in: body
          name: action
          description: Changes to apply for the video
          required: True
          schema:
            type: object
            properties:
              trim:
                type: string
                example: 5.1,10.5
              crop:
                type: string
                example: 480,360,10,10
              rotate:
                type: integer
                enum: [-270, -180, -90, 90, 180, 270]
                example: 90
              scale:
                type: integer
                example: 800
        responses:
          202:
            description: Editing started
            schema:
              type: object
              properties:
                processing:
                  type: boolean
                  example: True
          409:
            description: Previous editing was not finished yet
            schema:
              type: object
              properties:
                processing:
                  type: array
                  example:
                    - Task edit video is still processing
        """

        if self.project['processing']['video']:
            raise Conflict({"processing": ["Task edit video is still processing"]})

        if self.project['version'] == 1:
            raise BadRequest({"project_id": ["Video with version 1 is not editable, use duplicated project instead."]})

        request_json = request.get_json()
        document = validate_document(
            request_json if request_json else {},
            self.schema_edit
        )

        if not document:
            raise BadRequest({
                'edit': [f"At least one of the edit rules is required. "
                         f"Available edit rules are: {', '.join(self.schema_edit.keys())}"]
            })

        metadata = self.project['metadata']

        # validate trim
        if 'trim' in document:
            if document['trim']['start'] >= document['trim']['end']:
                raise BadRequest({"trim": ["'start' value must be less than 'end' value"]})
            elif (document['trim']['end'] - document['trim']['start'] < app.config.get('MIN_TRIM_DURATION')) \
                    or (metadata['duration'] - document['trim']['start'] < app.config.get('MIN_TRIM_DURATION')):
                raise BadRequest({"trim": [
                    f"Trimmed video duration must be at least {app.config.get('MIN_TRIM_DURATION')} seconds"
                ]})
            elif document['trim']['end'] > metadata['duration']:
                document['trim']['end'] = metadata['duration']
                logger.info(
                    f"Trimmed video endtime is greater than video duration, update it to equal duration, "
                    f"ID: {self.project['_id']}")
            elif document['trim']['start'] == 0 and document['trim']['end'] == metadata['duration']:
                raise BadRequest({"trim": ["'end' value of trim is duplicating an entire video"]})
        # validate crop
        if 'crop' in document:
            if metadata['width'] - document['crop']['x'] < app.config.get('MIN_VIDEO_WIDTH'):
                raise BadRequest({"crop": ["x is less than minimum allowed crop width"]})
            elif metadata['height'] - document['crop']['y'] < app.config.get('MIN_VIDEO_HEIGHT'):
                raise BadRequest({"crop": ["y is less than minimum allowed crop height"]})
            elif document['crop']['x'] + document['crop']['width'] > metadata['width']:
                raise BadRequest({"crop": ["width of crop's frame is outside a video's frame"]})
            elif document['crop']['y'] + document['crop']['height'] > metadata['height']:
                raise BadRequest({"crop": ["height of crop's frame is outside a video's frame"]})
        # validate scale
        if 'scale' in document:
            width = metadata['width']
            if 'crop' in document:
                width = document['crop']['width']
            if document['scale'] == width:
                raise BadRequest({"trim": ["video and crop option have exactly the same width"]})
            elif not app.config.get('ALLOW_INTERPOLATION') and document['scale'] > width:
                raise BadRequest({"trim": ["interpolation of pixels is not allowed"]})
            elif app.config.get('ALLOW_INTERPOLATION') \
                    and document['scale'] > width \
                    and width >= app.config.get('INTERPOLATION_LIMIT'):
                raise BadRequest({"trim": [
                    f"interpolation is permitted only for videos which have width less than "
                    f"{app.config.get('INTERPOLATION_LIMIT')}px"
                ]})

        # set processing flag
        self.project = app.mongo.db.projects.find_one_and_update(
            {'_id': self.project['_id']},
            {'$set': {'processing.video': True}},
            return_document=ReturnDocument.AFTER
        )
        logger.info(f"New project editing task was started. ID: {self.project['_id']}")
        save_activity_log("EDIT", self.project['_id'], document)

        # run task
        edit_video.delay(
            self.project,
            changes=document
        )

        return json_response({"processing": True}, status=202)

    def delete(self, project_id):
        """
        Delete project from db and related files from a storage.
        ---
        parameters:
        - name: project_id
          in: path
          type: string
          required: true
          description: Unique project id
        responses:
          204:
            description: NO CONTENT
        """

        # remove project dir from storage
        app.fs.delete_dir(self.project['storage_id'])
        logger.info(f"Project was deleted. ID: {self.project['_id']}")
        save_activity_log("DELETE", self.project['_id'])
        app.mongo.db.projects.delete_one({'_id': self.project['_id']})

        return json_response(status=204)


class DuplicateProject(MethodView):

    def post(self, project_id):
        """
        Duplicate project
        ---
        parameters:
            - name: project_id
              in: path
              type: string
              required: true
              description: Unique project id
        responses:
          201:
            description: Project was duplicated
            schema:
                type: object
                properties:
                  _id:
                    type: string
                    example: 5cbd5acfe24f6045607e51aa
                  filename:
                    type: string
                    example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                  storage_id:
                    type: string
                    example: 2019/7/2/5cbd5acfe24f6045607e51aa/9c8e970807104c848afceea44fa07d1a.mp4
                  metadata:
                    type: object
                    properties:
                      codec_name:
                        type: string
                        example: h264
                      codec_long_name:
                        type: string
                        example: H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
                      width:
                        type: int
                        example: 640
                      height:
                        type: int
                        example: 360
                      duration:
                        type: float
                        example: 300.014000
                      bit_rate:
                        type: int
                        example: 287654
                      nb_frames:
                        type: int
                        example: 7654
                      r_frame_rate:
                        type: string
                        example: 24/1
                      format_name:
                        type: string
                        example: mov,mp4,m4a,3gp,3g2,mj2
                      size:
                        type: int
                        example: 14567890
                  url:
                    type: string
                    example: http://localhost:5050/projects/5cbd5acfe24f6045607e51aa/raw/video
                  mime_type:
                    type: string
                    example: video/mp4
                  create_time:
                    type: string
                    example: 2019-07-02T15:02:32+00:00
                  original_filename:
                    type: string
                    example: video.mp4
                  request_address:
                    type: string
                    example: 127.0.0.1
                  version:
                    type: integer
                    example: 1
                  parent:
                    type: string
                    example: 5d2c8078fe985e7587b50de7
                  processing:
                    type: object
                    properties:
                      video:
                        type: boolean
                        example: False
                      thumbnail_preview:
                        type: boolean
                        example: False
                      thumbnails_timeline:
                        type: boolean
                        example: False
                  thumbnails:
                    type: object
                    properties:
                      timeline:
                        type: array
                        example: []
                      preview:
                        type: object
                        example: {}
          409:
            description: A running task has not completed
            schema:
              type: object
              properties:
                processing:
                  type: array
                  example:
                    - Some tasks is still processing
        """

        if any(self.project['processing'].values()):
            raise Conflict({"processing": ["Some tasks is still processing"]})

        # deepcopy & save a child_project
        child_project = copy.deepcopy(self.project)
        del child_project['_id']
        del child_project['storage_id']
        child_project['parent'] = self.project['_id']
        child_project['create_time'] = datetime.utcnow()
        child_project['version'] += 1
        child_project['thumbnails'] = {
            'timeline': [],
            'preview': {}
        }
        app.mongo.db.projects.insert_one(child_project)

        # put a video file stream into storage
        try:
            storage_id = app.fs.put(
                content=app.fs.get(self.project['storage_id']),
                filename=child_project['filename'],
                project_id=child_project['_id'],
                content_type=child_project['mime_type']
            )
        except Exception as e:
            # remove record from db
            app.mongo.db.projects.delete_one({'_id': child_project['_id']})
            raise InternalServerError(str(e))

        try:
            # set 'storage_id' for child_project
            child_project = app.mongo.db.projects.find_one_and_update(
                {'_id': child_project['_id']},
                {'$set': {'storage_id': storage_id}},
                return_document=ReturnDocument.AFTER
            )

            # save preview thumbnail
            if self.project['thumbnails']['preview']:
                storage_id = app.fs.put(
                    content=app.fs.get(self.project['thumbnails']['preview']['storage_id']),
                    filename=self.project['thumbnails']['preview']['filename'],
                    project_id=None,
                    asset_type='thumbnails',
                    storage_id=child_project['storage_id'],
                    content_type=self.project['thumbnails']['preview']['mimetype']
                )
                child_project['thumbnails']['preview'] = self.project['thumbnails']['preview']
                child_project['thumbnails']['preview']['storage_id'] = storage_id
                # set preview thumbnail in db
                child_project = app.mongo.db.projects.find_one_and_update(
                    {'_id': child_project['_id']},
                    {"$set": {
                        'thumbnails.preview': child_project['thumbnails']['preview']
                    }},
                    return_document=ReturnDocument.AFTER
                )

            # save timeline thumbnails
            timeline_thumbnails = []
            for thumbnail in self.project['thumbnails']['timeline']:
                storage_id = app.fs.put(
                    content=app.fs.get(thumbnail['storage_id']),
                    filename=thumbnail['filename'],
                    project_id=None,
                    asset_type='thumbnails',
                    storage_id=child_project['storage_id'],
                    content_type=thumbnail['mimetype']
                )
                timeline_thumbnails.append({
                    'filename': thumbnail['filename'],
                    'storage_id': storage_id,
                    'mimetype': thumbnail['mimetype'],
                    'width': thumbnail['width'],
                    'height': thumbnail['height'],
                    'size': thumbnail['size']
                })
            if timeline_thumbnails:
                child_project = app.mongo.db.projects.find_one_and_update(
                    {'_id': child_project['_id']},
                    {"$set": {
                        'thumbnails.timeline': timeline_thumbnails
                    }},
                    return_document=ReturnDocument.AFTER
                )

        except Exception as e:
            # delete child_project dir
            app.fs.delete_dir(storage_id)
            # remove record from db
            app.mongo.db.projects.delete_one({'_id': child_project['_id']})
            raise InternalServerError(str(e))

        logger.info(f"Project was duplicated. Parent ID: {self.project['_id']}. Child ID: {child_project['_id']}")
        save_activity_log('DUPLICATE', self.project['_id'], child_project)
        add_urls(child_project)

        return json_response(child_project, status=201)


class RetrieveOrCreateThumbnails(MethodView):
    SCHEMA_UPLOAD = {
        'file': {
            'type': 'filestorage',
            'required': True
        }
    }

    @property
    def schema_thumbnails(self):
        return {
            'type': {
                'type': 'string',
                'required': True,
                'anyof': [
                    {
                        'allowed': ['timeline'],
                        'dependencies': ['amount'],
                        'excludes': ['position', 'crop', 'rotate'],
                    },
                    {
                        # make `amount` optional
                        'allowed': ['timeline'],
                        'excludes': ['position', 'crop', 'rotate'],
                    },
                    {
                        'allowed': ['preview'],
                        'dependencies': ['position'],
                        'excludes': 'amount',
                    }
                ],
            },
            'amount': {
                'type': 'integer',
                'coerce': int,
                'min': 1,
            },
            'position': {
                'type': 'float',
                'coerce': float,
            },
            'crop': {
                'required': False,
                'regex': r'^\d+,\d+,\d+,\d+$',
                'coerce': 'crop_to_dict',
                'allow_crop_width': [app.config.get('MIN_VIDEO_WIDTH'), app.config.get('MAX_VIDEO_WIDTH')],
                'allow_crop_height': [app.config.get('MIN_VIDEO_HEIGHT'), app.config.get('MAX_VIDEO_HEIGHT')]
            },
            'rotate': {
                'type': 'integer',
                'required': False,
                'coerce': int,
                'allowed': [-270, -180, -90, 90, 180, 270]
            }
        }

    def get(self, project_id):
        """
        Get or create thumbnail for preview or thumbnails for timeline.
        If `type` is `timeline` - return a list of thumbnails for timeline or start task to generate thumbnails.
        If `type` is `preview` - return a preview thumbnail or start task to generate it.
        ---
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
          description: Unique project id
        - name: type
          in: query
          type: string
          enum: [preview, timeline]
        - name: amount
          in: query
          type: integer
          description: Amount of thumbnails to generate for a timeline. Used only when `type` is `timeline`.
        - name: position
          in: query
          type: float
          description: Position in the video where preview thumbnail should be captured.
                       Used only when `type` is `preview`.
        - name: crop
          in: query
          type: json
          description: Crop rules apply to preview thumbnail. Used only when `type` is `preview`.
          default: "0,0,720,360"
        - name: rotate
          in: query
          type: integer
          description: Number of degrees rotate preview thumbnail. Used only when `type` is `preview`.
          enum: [-270, -180, -90, 90, 180, 270]
        responses:
          200:
            description: Timeline/preview thumbnails information
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: c2deb6fb933d4df186ad2539914ff374_preview-4.0.png
                storage_id:
                  type: string
                  example: 2019/7/17/5cbd5acfe24f6045607e51aa/thumbnails/c2deb6fb933d4df186ad2539914ff374_preview-4.0.png  # noqa
                mimetype:
                  type: string
                  example: image/png
                width:
                  type: integer
                  example: 360
                height:
                  type: integer
                  example: 720
                size:
                  type: integer
                  example: 654321
                position:
                  type: integer
                  example: 10
                url:
                  type: string
                  example: http://localhost:5050/projects/5cbd5acfe24f6045607e51aa/raw/thumbnails/preview
          202:
            description: Timeline/preview thumbnails status that thumbnails generation task was started.
            schema:
              type: object
              properties:
                processing:
                  type: boolean
                  example: True
                thumbnails:
                  type: array
                  example: []
          409:
            description: Timeline/preview task is still processing
            schema:
              type: object
              properties:
                processing:
                  type: array
                  example:
                    - Task get preview thumbnails is still processing
        """
        document = validate_document(request.args.to_dict(), self.schema_thumbnails)
        add_urls(self.project)

        if document['type'] == 'timeline':
            return self._get_timeline_thumbnails(
                amount=document.get('amount', app.config.get('DEFAULT_TOTAL_TIMELINE_THUMBNAILS'))
            )

        return self._get_preview_thumbnail(document['position'], document.get('crop'), document.get('rotate', 0))

    def post(self, project_id):
        """
        Upload custom preview thumbnail.
        ---
        consumes:
         - multipart/form-data
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
          description: Unique project id
        - in: formData
          name: file
          description: image file
          required: True
        responses:
          200:
            description: OK
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: 059ec59cd21543d2a014687619a85ca7_preview-custom.jpeg
                url:
                  type: string
                  example: http://localhost:5050/projects/5d2ee69cfe985e50884006f9/raw/thumbnail?type=preview
                storage_id:
                  type: string
                  example: 2019/7/17/5d2ee69cfe985e50884006f9/thumbnails/059ec59cd21543d2a014687619_preview-custom.jpeg
                mime_type:
                  type: string
                  example: video/mp4
                width:
                  type: integer
                  example: 640
                height:
                  type: integer
                  example: 360
                size:
                  type: integer
                  example: 300000
                positoin:
                  type: string
                  example: custom
          409:
            description: There is a running preview thumbnails task
            schema:
              type: object
              properties:
                processing:
                  type: array
                  example:
                    - Task get preview thumbnails is still processing
        """

        # validate request
        if 'file' not in request.files:
            # to avoid TypeError: cannot serialize '_io.BufferedRandom' error
            raise BadRequest({"file": ["required field"]})
        document = validate_document(request.files, self.SCHEMA_UPLOAD)

        # validate codec
        file_stream = document['file'].stream.read()
        metadata = get_video_editor().get_meta(file_stream)
        if metadata.get('codec_name') not in app.config.get('CODEC_SUPPORT_IMAGE'):
            raise BadRequest({'file': [f"Codec: '{metadata.get('codec_name')}' is not supported."]})

        # check if busy
        if self.project['processing']['thumbnail_preview']:
            raise Conflict({"processing": ["Task get preview thumbnails is still processing"]})

        # save to fs
        thumbnail_filename = "{filename}_preview-custom.{original_ext}".format(
            filename=os.path.splitext(self.project['filename'])[0],
            original_ext=request.files['file'].filename.rsplit('.', 1)[-1].lower()
        )
        mimetype = app.config.get('CODEC_MIMETYPE_MAP')[metadata.get('codec_name')]
        if self.project['thumbnails']['preview']:
            # delete old file
            app.fs.delete(self.project['thumbnails']['preview']['storage_id'])

        storage_id = app.fs.put(
            content=file_stream,
            filename=thumbnail_filename,
            project_id=None,
            asset_type='thumbnails',
            storage_id=self.project['storage_id'],
            content_type=mimetype
        )

        # save new thumbnail info
        self.project = app.mongo.db.projects.find_one_and_update(
            {'_id': self.project['_id']},
            {'$set': {
                'thumbnails.preview': {
                    'filename': thumbnail_filename,
                    'storage_id': storage_id,
                    'mimetype': mimetype,
                    'width': metadata.get('width'),
                    'height': metadata.get('height'),
                    'size': metadata.get('size'),
                    'position': 'custom'
                }
            }},
            return_document=ReturnDocument.AFTER
        )
        add_urls(self.project)

        return json_response(self.project['thumbnails']['preview'])

    def _get_timeline_thumbnails(self, amount):
        """
        Get list or create thumbnails for timeline
        :param amount: amount of thumbnails
        :type amount: int
        :return: json response
        :rtype: flask.wrappers.Response
        """
        # resource is busy
        # request get timeline thumbnails while editing video may lead to conflict with timeline task
        # triggered by edit video right after it finished
        if self.project['processing']['video']:
            raise Conflict({"processing": ["Task get video is still processing"]})
        # no need to generate thumbnails
        elif amount == len(self.project['thumbnails']['timeline']):
            return json_response({
                "processing": False,
                "thumbnails": self.project['thumbnails']['timeline'],
            })
        if self.project['processing']['thumbnails_timeline'] is False:
            # set processing flag
            self.project = app.mongo.db.projects.find_one_and_update(
                {'_id': self.project['_id']},
                {'$set': {'processing.thumbnails_timeline': True}},
                return_document=ReturnDocument.AFTER
            )
            # run task
            generate_timeline_thumbnails.delay(
                self.project,
                amount
            )
        return json_response({
            "processing": True,
            "thumbnails": [],
        }, status=202)

    def _get_preview_thumbnail(self, position, crop, rotate):
        """
        Get or create thumbnail for preview
        :param position: video position to capture a frame
        :type position: int
        :param crop: crop editing rules
        :type crop: dict
        :param rotate: rotate degree
        :type rotate: int
        :return: json response
        :rtype: flask.wrappers.Response
        """
        # validate crop param
        if crop:
            if self.project['metadata']['width'] - crop['x'] < app.config.get('MIN_VIDEO_WIDTH'):
                raise BadRequest({"crop": ["x is less than minimum allowed crop width"]})
            elif self.project['metadata']['height'] - crop['y'] < app.config.get('MIN_VIDEO_HEIGHT'):
                raise BadRequest({"crop": ["y is less than minimum allowed crop height"]})
            elif crop['x'] + crop['width'] > self.project['metadata']['width']:
                raise BadRequest({"crop": ["width of crop's frame is outside a video's frame"]})
            elif crop['y'] + crop['height'] > self.project['metadata']['height']:
                raise BadRequest({"crop": ["height of crop's frame is outside a video's frame"]})
        # validate position param
        if self.project['metadata']['duration'] < position:
            position = self.project['metadata']['duration']
            logger.info(f"Postition greater than video duration, Update it equal duration, ID: {self.project['_id']}")
        # resource is busy
        if self.project['processing']['thumbnail_preview']:
            raise Conflict({"processing": ["Task get preview thumbnails video is still processing"]})
        else:
            # set processing flag
            self.project = app.mongo.db.projects.find_one_and_update(
                {'_id': self.project['_id']},
                {'$set': {'processing.thumbnail_preview': True}},
                return_document=ReturnDocument.AFTER
            )
            # run task
            generate_preview_thumbnail.delay(
                self.project,
                position,
                crop,
                rotate,
            )
            return json_response({"processing": True}, status=202)


class GetRawVideo(MethodView):
    def get(self, project_id):
        """
        Get video stream.
        If `HTTP_RANGE` header is specified - return chunked video stream, else full file.
        ---
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
        produces:
          - video/mp4
        responses:
          200:
            description: Video stream
            content:
              video/mp4:
                schema:
                  type: string
                  format: binary
          206:
            description: Chunked stream
            content:
              video/mp4:
                schema:
                  type: string
                  format: binary
          409:
            description: Timeline/preview task is still processing
            schema:
              type: object
              properties:
                processing:
                  type: array
                  example:
                    - Task edit video is still processing
        """

        # video is processing
        if self.project['processing']['video']:
            raise Conflict({"processing": ["Task edit video is still processing"]})

        # get stream file for video
        video_range = request.headers.environ.get('HTTP_RANGE')
        length = self.project['metadata'].get('size')
        if video_range:
            # http range bytes=0-
            _range = re.split('[= | -]', video_range)
            start = int(_range[1])
            # TODO doublecheck streaming range
            end = length - 1
            # handle end range part in case of bytes=100-200
            if len(_range) == 3 and _range[2]:
                end = int(_range[2])
            chunksize = end - start + 1

            return storage2response(
                storage_id=self.project['storage_id'],
                headers={
                    'Content-Range': f'bytes {start}-{end}/{length}',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': chunksize,
                    'Content-Type': self.project.get("mime_type"),
                },
                status=206,
                start=start,
                length=chunksize
            )

        return storage2response(
            storage_id=self.project.get('storage_id'),
            headers={
                'Content-Length': length,
                'Content-Type': self.project.get("mime_type"),
            }
        )


class GetRawPreviewThumbnail(MethodView):

    def get(self, project_id):
        """
        Get preview thumbnail file
        ---
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
          description: Unique project id
        produces:
          - image/png
        responses:
          200:
            description: preview thumbnail image
            content:
              image/png:
                schema:
                  type: string
                  format: binary
        """

        if not self.project['thumbnails']['preview']:
            raise NotFound()

        return storage2response(
            storage_id=self.project['thumbnails']['preview']['storage_id'],
            headers={'Content-Type': self.project['thumbnails']['preview']['mimetype']}
        )


class GetRawTimelineThumbnail(MethodView):

    def get(self, project_id, index):
        """
        Get timeline thumbnail file
        ---
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
          description: Unique project id
        - in: path
          name: index
          type: integer
          required: True
          description: Index of timeline thumbnail to read.
        produces:
          - image/png
        responses:
          200:
            description: timeline thumbnail image
            content:
              image/png:
                schema:
                  type: string
                  format: binary
        """

        try:
            thumbnail = self.project['thumbnails']['timeline'][index]
        except IndexError:
            raise NotFound()

        return storage2response(
            storage_id=thumbnail['storage_id'],
            headers={'Content-Type': thumbnail['mimetype']}
        )


# register all urls
bp.add_url_rule(
    '/',
    view_func=ListUploadProject.as_view('list_upload_project')
)
bp.add_url_rule(
    '/<project_id>',
    view_func=RetrieveEditDestroyProject.as_view('retrieve_edit_destroy_project')
)
bp.add_url_rule(
    '/<project_id>/duplicate',
    view_func=DuplicateProject.as_view('duplicate_project')
)
bp.add_url_rule(
    '/<project_id>/thumbnails',
    view_func=RetrieveOrCreateThumbnails.as_view('retrieve_or_create_thumbnails')
)
bp.add_url_rule(
    '/<project_id>/raw/video',
    view_func=GetRawVideo.as_view('get_raw_video')
)
bp.add_url_rule(
    '/<project_id>/raw/thumbnails/preview',
    view_func=GetRawPreviewThumbnail.as_view('get_raw_preview_thumbnail')
)
bp.add_url_rule(
    '/<project_id>/raw/thumbnails/timeline/<int:index>',
    view_func=GetRawTimelineThumbnail.as_view('get_raw_timeline_thumbnail')
)
