import base64
import logging
import os
import re
from datetime import datetime

from bson import json_util
from flask import request, make_response
from flask import current_app as app
from pymongo import ReturnDocument
from pymongo.errors import ServerSelectionTimeoutError
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

from lib.utils import (
    create_file_name, json_response, get_url_for_media, validate_document,
    get_request_address, save_activity_log, paginate
)
from lib.video_editor import get_video_editor
from lib.views import MethodView

from .tasks import task_edit_video, generate_timeline_thumbnails, generate_preview_thumbnail
from . import bp

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
        Create new project record in DB and save file into file storage
        ---
        consumes:
          - multipart/form-data
        parameters:
        - in: formData
          name: file
          type: file
          description: file object to upload
        responses:
          201:
            description: CREATED
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                url:
                  type: string
                  example: https://example.com/url_raw/fa5079a38e0a4197864aa2ccb07f3bea4
                storage_id:
                  type: string
                  example: 2019/5/1/fa5079a38e0a4197864aa2ccb07f3bea.mp4
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
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: string
                  example: 2019-05-01T09:00:00+00:00
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
                  type: object
                  example: {}
                processing:
                  type: boolean
                  example: False
                thumbnails:
                  type: object
                  example: {}
                _id:
                  type: string
                  example: 5cbd5acfe24f6045607e51aa
        """

        # validate request
        if 'file' not in request.files:
            # to avoid TypeError: cannot serialize '_io.BufferedRandom' error
            raise BadRequest({"file": ["required field"]})
        document = validate_document(request.files, self.SCHEMA_UPLOAD)

        # validate codec
        file_stream = document['file'].stream.read()
        metadata = get_video_editor().get_meta(file_stream)
        if metadata.get('codec_name') not in app.config.get('CODEC_SUPPORT'):
            raise BadRequest(f"Codec: '{metadata.get('codec_name')}' is not supported.")

        # add record to database
        project = {
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
                'preview': None
            },
        }
        app.mongo.db.projects.insert_one(project)

        # put file stream into storage
        try:
            storage_id = app.fs.put(
                content=file_stream,
                filename=project['filename'],
                project_id=project['_id'],
                content_type=document['file'].mimetype
            )
        except Exception as e:
            # remove record from db
            app.mongo.db.projects.delete_one({'_id': project['_id']})
            raise InternalServerError(str(e))

        # set 'storage_id' for project
        try:
            project = app.mongo.db.projects.find_one_and_update(
                {'_id': project['_id']},
                {'$set': {'storage_id': storage_id}},
                return_document=ReturnDocument.AFTER
            )
        except ServerSelectionTimeoutError as e:
            # delete project dir
            app.fs.delete_dir(storage_id)
            # remove record from db
            app.mongo.db.projects.delete_one({'_id': project['_id']})
            raise InternalServerError(str(e))

        save_activity_log('upload', project['_id'])

        return json_response(project, status=201)

    def get(self):
        """
        Get list of projects in DB
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
                      filename:
                        type: string
                        example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                      url:
                        type: string
                        example: https://example.com/url_raw/fa5079a38e0a4197864aa2ccb07f3bea
                      storage_id:
                        type: string
                        example: 2019/5/fa5079a38e0a4197864aa2ccb07f3bea.mp4
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
                      mime_type:
                        type: string
                        example: video/mp4
                      create_time:
                        type: string
                        example: 2019-05-01T09:00:00+00:00
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
                        type: object
                        example: {}
                      processing:
                        type: boolean
                        example: False
                      thumbnails:
                        type: object
                        example: {}
                      _id:
                        type: string
                        example: 5cbd5acfe24f6045607e51aa
        """

        page = request.args.get('page', 1, type=int)
        projects = list(paginate(
            cursor=app.mongo.db.projects.find(),
            page=page
        ))

        return json_response(
            {
                '_items': projects,
                '_meta': {
                    'page': page,
                    'max_results': app.config.get('ITEMS_PER_PAGE'),
                    'total': app.mongo.db.projects.count()
                }
            }
        )


class RetrieveEditDestroyProject(MethodView):
    SCHEMA_EDIT = {
        'capture': {
            'type': 'dict',
            'required': False,
            'empty': True,
        },
        'cut': {
            'type': 'dict',
            'required': False,
            'empty': True,
            'schema': {
                'start': {'type': 'float', 'required': True},
                'end': {'type': 'float', 'required': True},
            },
        },
        'rotate': {
            'type': 'dict',
            'required': False,
            'empty': True,
            'schema': {
                'degree': {'type': 'integer', 'required': True}
            },
        },
        'quality': {
            'type': 'dict',
            'required': False,
            'empty': True,
        },
        'crop': {
            'type': 'dict',
            'required': False,
            'empty': True,
            'schema': {
                'width': {'type': 'float', 'required': True},
                'height': {'type': 'float', 'required': True},
                'x': {'type': 'float', 'required': True},
                'y': {'type': 'float', 'required': True}
            }
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
            description: OK
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                url:
                  type: string
                  example: https://example.com/url_raw/fa5079a38e0a4197864aa2ccb07f3bea
                storage_id:
                  type: string
                  example: 2019/5/fa5079a38e0a4197864aa2ccb07f3bea.mp4
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
                      type: integer
                      example: 640
                    height:
                      type: integer
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
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: string
                  example: 2019-05-01T09:00:00+00:00
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
                  type: object
                  example: {}
                processing:
                  type: boolean
                  example: False
                thumbnails:
                  type: object
                  example: {}
                _id:
                  type: string
                  example: 5cbd5acfe24f6045607e51aa
        """

        return json_response(self._project)

    def put(self, project_id):
        """
        Edit video. This method does not create a new project.
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
          description: Actions want to apply to the video
          required: True
          schema:
            type: object
            properties:
              cut:
                type: object
                properties:
                  start:
                    type: integer
                    example: 5
                  end:
                    type: integer
                    example: 10
              crop:
                type: object
                properties:
                  width:
                    type: integer
                    example: 480
                  height:
                    type: integer
                    example: 360
                  x:
                    type: integer
                    example: 10
                  y:
                    type: integer
                    example: 10
              rotate:
                type: object
                properties:
                  degree:
                    type: integer
                    example: 90
        responses:
          200:
            description: OK
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                url:
                  type: string
                  example: https://example.com/url_raw/fa5079a38e0a4197864aa2ccb07f3bea
                storage_id:
                  type: string
                  example: 2019/5/fa5079a38e0a4197864aa2ccb07f3bea.mp4
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
                      type: integer
                      example: 640
                    height:
                      type: integer
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
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: string
                  example: 2019-05-01T09:00:00+00:00
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
                  type: object
                  example: {}
                processing:
                  type: boolean
                  example: False
                thumbnails:
                  type: object
                  example: {}
                _id:
                  type: string
                  example: 5cbd5acfe24f6045607e51aa
        """
        document = validate_document(request.get_json(), self.SCHEMA_EDIT)

        if self._project.get('processing') is True:
            return json_response({'processing': self._project['processing']}, status=202)
        if not self._project.get('version') >= 2:
            raise BadRequest("Only PUT action for edited video version 2")

        # Update processing is True when begin edit video
        doc = app.mongo.db.projects.find_one_and_update(
            {'_id': self._project['_id']},
            {'$set': {
                'processing': True,
            }},
            return_document=ReturnDocument.AFTER
        )
        save_activity_log("PUT PROJECT", doc['_id'], document)
        task_edit_video.delay(json_util.dumps(doc), document, action='put')
        return json_response(doc)

    def post(self, project_id):
        """
        Edit video. This method creates a new project.
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
          description: Actions want to apply to the video
          required: True
          schema:
            type: object
            properties:
              cut:
                type: object
                properties:
                  start:
                    type: integer
                    example: 5
                  end:
                    type: integer
                    example: 10
              crop:
                type: object
                properties:
                  width:
                    type: integer
                    example: 480
                  height:
                    type: integer
                    example: 360
                  x:
                    type: integer
                    example: 10
                  y:
                    type: integer
                    example: 10
              rotate:
                type: object
                properties:
                  degree:
                    type: integer
                    example: 90
        responses:
          200:
            description: OK
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: fa5079a38e0a4197864aa2ccb07f3bea_v2.mp4
                url:
                  type: string
                  example: https://example.com/url_raw/fa5079a38e0a4197864aa2ccb07f3bea
                storage_id:
                  type: string
                  example: 2019/5/fa5079a38e0a4197864aa2ccb07f3bea.mp4
                metadata:
                  type: object
                  example: {}
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: string
                  example: 2019-05-01T09:00:00+00:00
                original_filename:
                  type: string
                  example: video.mp4
                request_address:
                  type: string
                  example: 127.0.0.1
                version:
                  type: integer
                  example: 2
                parent:
                  type: object
                  parameters:
                    _id:
                      type: object
                      parameters:
                        $oid:
                          type: string
                          example: 5ccbc4104dfd9b8fa153d60e
                processing:
                  type: boolean
                  example: False
                thumbnails:
                  type: object
                  example: {}
                _id:
                  type: string
                  example: 5cbd5acfe24f6045607e51aa
        """
        document = validate_document(request.get_json(), self.SCHEMA_EDIT)

        filename, ext = os.path.splitext(self._project['filename'])
        if self._project.get('version') >= 2:
            raise BadRequest("Only POST action for original video version 1")
        version = self._project.get('version', 1) + 1
        new_file_name = f'{filename}_v{version}{ext}'
        new_doc = {
            'filename': new_file_name,
            'storage_id': self._project.get('storage_id'),
            'metadata': None,
            'request_address': get_request_address(request.headers.environ),
            'version': version,
            'processing': True,
            'mime_type': self._project.get('mime_type'),
            'parent': {
                '_id': self._project.get('_id'),
            },
            'thumbnails': {},
            'preview_thumbnail': self._project.get('preview_thumbnail')
        }
        app.mongo.db.projects.insert_one(new_doc)
        new_doc['predict_url'] = get_url_for_media(new_doc.get('_id'), 'video')
        task_edit_video.delay(json_util.dumps(new_doc), document)
        save_activity_log("POST PROJECT", self._project['_id'], document)
        return json_response(new_doc)

    def delete(self, project_id):
        """
        Delete project from db and video from filestorage.
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
        app.fs.delete_dir(self._project['storage_id'])
        save_activity_log("DELETE PROJECT", self._project['_id'])
        app.mongo.db.projects.delete_one({'_id': self._project['_id']})

        return json_response(status=204)


class RetrieveOrCreateThumbnails(MethodView):
    SCHEMA_THUMBNAILS = {
        'type': {
            'type': 'string',
            'required': True,
            'anyof': [
                {
                    'allowed': ['timeline'],
                    'dependencies': ['amount'],
                    'excludes': 'position',
                },
                {
                    # make `amount` optional
                    'allowed': ['timeline'],
                    'excludes': 'position',
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
    }

    SCHEMA_UPLOAD = {
        'data': {
            'type': 'string',
            'required': True,
            'empty': False,
        }
    }

    def get(self, project_id):
        """
        Get or capture video thumbnails.
        Generate new thumbnails if it is empty or `amount` argument different from current total thumbnails.
        Or capture preview thumbnail at `position`.
        ---
        consumes:
        - application/json
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
          description: Unique project id
        - name: amount
          in: query
          type: integer
          description: number thumbnails to create
        - name: position
          in: query
          type: float
          description: position to capture preview thumbnail
        responses:
          200:
            description: OK
            schema:
              type: object
              properties:
                processing:
                  type: boolean
                  example: True
                thumbnails:
                  type: object
                  example: {}
        """
        document = validate_document(request.args.to_dict(), self.SCHEMA_THUMBNAILS)

        if document['type'] == 'timeline':
            return self._get_timeline_thumbnails(
                amount=document.get('amount', app.config.get('DEFAULT_TOTAL_TIMELINE_THUMBNAILS'))
            )

        return self._get_preview_thumbnail(document['position'])

    def post(self, project_id):
        """
        Update video preview thumbnails
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
          name: body
          description: Thumbnail data
          required: True
          schema:
            type: object
            properties:
              data:
                type: string
                description: base64 image data want to upload
        responses:
          200:
            description: OK
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                url:
                  type: string
                  example: https://example.com/url_raw/fa5079a38e0a4197864aa2ccb07f3bea
                storage_id:
                  type: string
                  example: 2019/5/fa5079a38e0a4197864aa2ccb07f3bea.mp4
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
                      type: string
                      example: 640
                    height:
                      type: string
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
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: string
                  example: 2019-05-01T09:00:00+00:00
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
                  type: object
                  example: {}
                processing:
                  type: boolean
                  example: False
                thumbnails:
                  type: object
                  example: {}
                _id:
                  type: string
                  example: 5cbd5acfe24f6045607e51aa
                preview_thumbnail:
                  type: object
                  properties:
                    filename:
                      type: string
                      example: fa5079a38e0a4197864aa2ccb07f3bea_thumbnail.png
                    storage_id:
                      type: string
                      example: 2019/5/fa5079a38e0a4197864aa2ccb07f3bea_thumbnail.png
                    mimetype:
                      type: string
                      example: "image/png"
                    width:
                      type: integer
                      example: 640
                    height:
                      type: integer
                      example: 360
                    size:
                      type: int
                      example: 300000
        """

        document = validate_document(request.get_json(), self.SCHEMA_UPLOAD)

        if self._project.get('processing') is True:
            return json_response({'processing': self._project['processing']}, status=202)

        base64_string = document['data']
        try:
            if ',' not in base64_string:
                base64_thumbnail = base64_string
            else:
                base64_format, base64_thumbnail = base64_string.split(',', 1)
            thumbnail_stream = base64.b64decode(base64_thumbnail)
        except base64.binascii.Error as err:
            raise BadRequest(str(err))

        video_editor = get_video_editor()
        thumbnail_metadata = video_editor.get_meta(thumbnail_stream, 'png')
        return self._save_thumbnail(self._project, thumbnail_stream, thumbnail_metadata)

    def _get_timeline_thumbnails(self, amount):
        """
        Get list or create thumbnails for timeline
        :param amount: amount of thumbnails
        :return: json response
        """
        # resource is busy
        if self._project['processing']['thumbnails_timeline']:
            return json_response({"processing": True}, status=202)
        # no need to generate thumbnails
        elif amount == len(self._project['thumbnails']['timeline']):
            return json_response({"thumbnails": self._project['thumbnails']['timeline']})
        else:
            # set processing flag
            self._project = app.mongo.db.projects.find_one_and_update(
                {'_id': self._project['_id']},
                {'$set': {'processing.thumbnails_timeline': True}},
                return_document=ReturnDocument.AFTER
            )
            # run task
            generate_timeline_thumbnails.delay(
                json_util.dumps(self._project),
                amount
            )
            return json_response({"processing": True}, status=202)

    def _get_preview_thumbnail(self, position):
        """
        Get or create thumbnail for preview
        :param position: video position to capture a frame
        :return: json response
        """
        # resource is busy
        if self._project['processing']['thumbnail_preview']:
            return json_response({"processing": True}, status=202)
        elif (self._project['thumbnails']['preview'] and
              self._project['thumbnails']['preview'].get('position') == position):
            return json_response({"thumbnails": self._project['thumbnails']['preview']})
        elif self._project['metadata']['duration'] < position:
            return BadRequest(
                f"Requested position:{position} is more than video's duration:{self._project['metadata']['duration']}."
            )
        else:
            # set processing flag
            self._project = app.mongo.db.projects.find_one_and_update(
                {'_id': self._project['_id']},
                {'$set': {'processing.thumbnail_preview': True}},
                return_document=ReturnDocument.AFTER
            )
            # run task
            generate_preview_thumbnail.delay(
                json_util.dumps(self._project),
                position
            )
            return json_response({"processing": True}, status=202)

    def _save_thumbnail(self, doc, stream, metadata):
        filename, ext = os.path.splitext(doc['filename'])
        thumbnail_filename = f"{filename}_thumbnail.png"
        storage_id = app.fs.put(
            stream, thumbnail_filename, None,
            asset_type='thumbnails', storage_id=doc['storage_id'], content_type='image/png'
        )
        doc = app.mongo.db.projects.find_one_and_update(
            {'_id': doc['_id']},
            {'$set': {
                'preview_thumbnail': {
                    'filename': thumbnail_filename,
                    'url': get_url_for_media(doc.get('_id'), 'thumbnail'),
                    'storage_id': storage_id,
                    'mimetype': 'image/png',
                    'width': metadata.get('width'),
                    'height': metadata.get('height'),
                    'size': metadata.get('size'),
                }
            }},
            return_document=ReturnDocument.AFTER
        )
        return json_response(doc)


class GetRawVideo(MethodView):
    def get(self, project_id):
        """
        Get video
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
            description: OK
            schema:
              type: file
        """

        # video is processing
        if self._project['processing']['video']:
            return json_response({'processing': True}, status=202)

        # get stream file for video
        video_range = request.headers.environ.get('HTTP_RANGE')
        length = self._project['metadata'].get('size')
        if video_range:
            start = int(re.split('[= | -]', video_range)[1])
            end = length - 1
            chunksize = end - start + 1
            headers = {
                'Content-Range': f'bytes {start}-{end}/{length}',
                'Accept-Ranges': 'bytes',
                'Content-Length': chunksize,
                'Content-Type': self._project.get("mime_type"),
            }
            # get a stack of bytes push to client
            stream = app.fs.get_range(self._project['storage_id'], start, chunksize)
            res = make_response(stream)
            res.headers = headers
            return res, 206

        headers = {
            'Content-Length': length,
            'Content-Type': 'video/mp4',
        }
        stream = app.fs.get(self._project.get('storage_id'))
        res = make_response(stream)
        res.headers = headers
        return res, 200


class GetRawThumbnail(MethodView):
    SCHEME_THUMBNAIL = {
        'index': {
            'type': 'integer',
            'required': False,
            'empty': True,
            'coerce': int,
            'min': 0,
        },
    }

    def get(self, project_id):
        """
        Get thumbnail
        ---
        parameters:
        - in: path
          name: project_id
          type: string
          required: True
          description: Unique project id
        - name: index
          in: query
          type:
          - integer
          - string
          description: index of thumbnail to get, leave empty to get preview thumbnail
        produces:
          - image/png
        responses:
          200:
            description: OK
            schema:
              type: file
        """

        if not request.args:
            preview_thumbnail = self._project.get('preview_thumbnail')
            if not preview_thumbnail:
                raise NotFound()
            byte = app.fs.get(preview_thumbnail.get('storage_id'))
        else:
            document = validate_document(request.args.to_dict(), self.SCHEME_THUMBNAIL, allow_unknown=True)
            index = document['index']
            thumbnails = next(iter(self._project['thumbnails'].values()), [])
            if len(thumbnails) < index + 1:
                raise NotFound()
            byte = app.fs.get(thumbnails[index]['storage_id'])

        res = make_response(byte)
        res.headers['Content-Type'] = 'image/png'
        return res


# register all urls
bp.add_url_rule('/', view_func=ListUploadProject.as_view('upload_project'))
bp.add_url_rule('/<project_id>', view_func=RetrieveEditDestroyProject.as_view('retrieve_edit_destroy_project'))
bp.add_url_rule('/<project_id>/thumbnails',
                view_func=RetrieveOrCreateThumbnails.as_view('retrieve_or_create_thumbnails'))
bp.add_url_rule('/<project_id>/url_raw/video', view_func=GetRawVideo.as_view('get_raw_video'))
bp.add_url_rule('/<project_id>/url_raw/thumbnail', view_func=GetRawThumbnail.as_view('get_raw_thumbnail'))
