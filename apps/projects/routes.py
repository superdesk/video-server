import base64
import logging
import os
import re
from datetime import datetime

from bson import json_util, ObjectId
from flask import request, make_response
from flask import current_app as app
from flask.views import MethodView
from pymongo import ReturnDocument
from pymongo.errors import ServerSelectionTimeoutError
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

from lib.utils import create_file_name, json_response, get_url_for_media
from lib.validator import Validator
from lib.video_editor import get_video_editor

from . import bp
from .tasks import task_edit_video, task_get_list_thumbnails

logger = logging.getLogger(__name__)


def check_request_schema_validity(request_schema, schema, **kwargs):
    validator = Validator(schema, **kwargs)
    if not validator.validate(request_schema):
        raise BadRequest(validator.errors)
    return validator.document


def get_request_address(request_headers):
    return request_headers.get('HTTP_X_FORWARDED_FOR') or request_headers.get('REMOTE_ADDR')


def find_one_or_404(project_id):
    # Flask-PyMongo find_one_or_404 method uses abort so can't pass custom 404 error message
    doc = app.mongo.db.projects.find_one({'_id': ObjectId(project_id)})
    if not doc:
        raise NotFound(f"Project with id {project_id} was not found.")
    return doc


def save_activity_log(action, project_id, storage_id, payload=None):
    app.mongo.db.activity.insert_one({
        "action": action,
        "project_id": project_id,
        "storage_id": storage_id,
        "payload": payload,
        "create_date": datetime.utcnow()
    })


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

        schema = check_request_schema_validity(request.files, self.SCHEMA_UPLOAD)

        # validate codec
        video_editor = get_video_editor()
        file = schema['file']
        file_stream = file.stream.read()
        metadata = video_editor.get_meta(file_stream)
        codec_name = metadata.get('codec_name')
        if codec_name not in app.config.get('CODEC_SUPPORT'):
            raise BadRequest("Codec: {} is not supported.".format(codec_name))
        # generate file name
        file_name = create_file_name(ext=file.filename.split('.')[1])
        try:
            # add record to database
            doc = {
                'filename': file_name,
                'storage_id': None,
                'metadata': metadata,
                'create_time': datetime.utcnow(),
                'mime_type': file.mimetype,
                'version': 1,
                'processing': False,
                'parent': None,
                'thumbnails': {},
                'request_address': get_request_address(request.headers.environ),
                'original_filename': file.filename,
                'preview_thumbnail': None,
                'url': None
            }
            app.mongo.db.projects.insert_one(doc)

            # put file stream into storage
            storage_id = app.fs.put(file_stream, file_name, doc['_id'], content_type=file.mimetype)
            if not storage_id:
                raise InternalServerError('Something went wrong when putting file into storage.')

            # update url for preview video
            doc = app.mongo.db.projects.find_one_and_update(
                {'_id': doc['_id']},
                {'$set': {
                    'storage_id': storage_id,
                    'url': get_url_for_media(doc.get('_id'), 'video'),
                }},
                return_document=ReturnDocument.AFTER
            )
            save_activity_log("UPLOAD", doc['_id'], doc['storage_id'], {"file": doc.get('filename')})
            return json_response(doc, status=201)
        except ServerSelectionTimeoutError:
            app.fs.delete(file_name)
            raise InternalServerError('Could not connect to database')
        except Exception as ex:
            app.fs.delete(file_name)
            logger.exception(ex)
            raise InternalServerError(str(ex))

    def get(self):
        """
        Get list of projects in DB
        ---
        parameters:
        - name: offset
          in: query
          type: integer
          description: Page number
        responses:
          200:
            description: OK
            schema:
              type: object
              properties:
                offset:
                  type: integer
                  example: 1
                size:
                  type: integer
                  example: 14
                max_size:
                  type: integer
                  example: 50
                items:
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
        offset = request.args.get('offset', 0, type=int)
        size = app.config.get('ITEMS_PER_PAGE', 25)
        # get all projects
        docs = list(app.mongo.db.projects.find().skip(offset).limit(size))

        res = {
            'items': docs,
            'offset': offset,
            'max_results': size,
            'total': app.mongo.db.projects.count()
        }
        return json_response(res)


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

        doc = find_one_or_404(project_id)
        return json_response(doc)

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
        schema = check_request_schema_validity(request.get_json(), self.SCHEMA_EDIT)

        doc = find_one_or_404(project_id)
        if doc.get('processing') is True:
            return json_response({'processing': doc['processing']}, status=202)
        if not doc.get('version') >= 2:
            raise BadRequest("Only PUT action for edited video version 2")

        # Update processing is True when begin edit video
        doc = app.mongo.db.projects.find_one_and_update(
            {'_id': doc['_id']},
            {'$set': {
                'processing': True,
            }},
            return_document=ReturnDocument.AFTER
        )
        save_activity_log("PUT PROJECT", doc['_id'], doc['storage_id'], schema)
        task_edit_video.delay(json_util.dumps(doc), schema, action='put')
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
        schema = check_request_schema_validity(request.get_json(), self.SCHEMA_EDIT)

        doc = find_one_or_404(project_id)

        filename, ext = os.path.splitext(doc['filename'])
        if doc.get('version') >= 2:
            raise BadRequest("Only POST action for original video version 1")
        version = doc.get('version', 1) + 1
        new_file_name = f'{filename}_v{version}{ext}'
        new_doc = {
            'filename': new_file_name,
            'storage_id': doc.get('storage_id'),
            'metadata': None,
            'request_address': get_request_address(request.headers.environ),
            'version': version,
            'processing': True,
            'mime_type': doc.get('mime_type'),
            'parent': {
                '_id': doc.get('_id'),
            },
            'thumbnails': {},
            'preview_thumbnail': doc.get('preview_thumbnail')
        }
        app.mongo.db.projects.insert_one(new_doc)
        new_doc['predict_url'] = get_url_for_media(new_doc.get('_id'), 'video')
        task_edit_video.delay(json_util.dumps(new_doc), schema)
        save_activity_log("POST PROJECT", doc['_id'], doc['storage_id'], schema)
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
        doc = find_one_or_404(project_id)

        # remove file from storage
        if app.fs.delete(doc['storage_id']):
            # Delete thumbnails
            for thumbnail in next(iter(doc['thumbnails'].values()), []):
                app.fs.delete(thumbnail['storage_id'])
            preview_thumbnail = doc['preview_thumbnail']
            if preview_thumbnail:
                app.fs.delete(preview_thumbnail['storage_id'])

            save_activity_log("DELETE PROJECT", doc['_id'], doc['storage_id'], None)
            app.mongo.db.projects.delete_one({'_id': ObjectId(project_id)})
            return json_response(status=204)
        else:
            raise InternalServerError()


class RetrieveOrCreateThumbnails(MethodView):
    SCHEMA_THUMBNAILS = {
        'type': {
            'type': 'string',
            'required': True,
            'anyof': [
                {
                    'allowed': ['timeline'],
                    'dependencies': ['amount'],
                    'excludes': 'time',
                },
                {  # make amount optional
                    'allowed': ['timeline'],
                    'excludes': 'time',
                },
                {
                    'allowed': ['preview'],
                    'dependencies': ['time'],
                    'excludes': 'amount',
                }
            ],
        },
        'amount': {
            'type': 'integer',
            'coerce': int,
            'min': 1,
        },
        'time': {
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
        Or capture thumbnail at `time`.
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
        - name: time
          in: query
          type: float
          description: time to capture preview thumbnail
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
        doc = find_one_or_404(project_id)
        schema = check_request_schema_validity(request.args.to_dict(), self.SCHEMA_THUMBNAILS)

        if schema['type'] == 'timeline':
            return self._get_timeline_thumbnail(
                doc,
                schema.get('amount', app.config.get('DEFAULT_TOTAL_TIMELINE_THUMBNAILS'))
            )
        else:
            return self._capture_thumbnail(doc, schema['time'])

    def _get_timeline_thumbnail(self, doc, amount):
        # Only get thumbnails when list thumbnail have not created yet (empty) and video is not processed any task
        data = doc.get('thumbnails')
        if (not data or not data.get(str(amount))) \
                and doc.get('processing') is False:

            # Delete all old thumbnails

            for thumbnail in next(iter(doc['thumbnails'].values()), []):
                app.fs.delete(thumbnail['storage_id'])

            # Update processing is True when begin edit video
            doc = app.mongo.db.projects.find_one_and_update(
                {'_id': doc['_id']},
                {'$set': {
                    'processing': True,
                    'thumbnails': {}
                }},
                return_document=ReturnDocument.AFTER
            )
            # Run get list thumbnails of timeline for video in celery
            task_get_list_thumbnails.delay(json_util.dumps(doc), amount)
        return json_response({
            "processing": doc.get('processing'),
            "thumbnails": doc['thumbnails'],
        })

    def _capture_thumbnail(self, doc, time):
        video_editor = get_video_editor()
        video_stream = app.fs.get(doc['storage_id'])

        thumbnail_stream, thumbnail_metadata = video_editor.capture_thumbnail(
            video_stream, doc['filename'], doc['metadata'], time
        )
        return self._save_thumbnail(doc, thumbnail_stream, thumbnail_metadata)

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
        doc = find_one_or_404(project_id)

        schema = check_request_schema_validity(request.get_json(), self.SCHEMA_UPLOAD)

        if doc.get('processing') is True:
            return json_response({'processing': doc['processing']}, status=202)

        base64_string = schema['data']
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
        return self._save_thumbnail(doc, thumbnail_stream, thumbnail_metadata)

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
        project_id, _ = os.path.splitext(project_id)
        doc = app.mongo.db.projects.find_one_or_404({'_id': ObjectId(project_id)})
        # video is processing
        if not doc['metadata']:
            return json_response({'processing': doc['processing']}, status=202)

        # get strem file for video
        video_range = request.headers.environ.get('HTTP_RANGE')
        length = doc['metadata'].get('size')
        if video_range:
            start = int(re.split('[= | -]', video_range)[1])
            end = length - 1
            chunksize = end - start + 1
            headers = {
                'Content-Range': f'bytes {start}-{end}/{length}',
                'Accept-Ranges': 'bytes',
                'Content-Length': chunksize,
                'Content-Type': doc.get("mime_type"),
            }
            # get a stack of bytes push to client
            stream = app.fs.get_range(doc['storage_id'], start, chunksize)
            res = make_response(stream)
            res.headers = headers
            return res, 206

        headers = {
            'Content-Length': length,
            'Content-Type': 'video/mp4',
        }
        stream = app.fs.get(doc.get('storage_id'))
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
        doc = app.mongo.db.projects.find_one_or_404({'_id': ObjectId(project_id)})

        if not request.args:
            preview_thumbnail = doc.get('preview_thumbnail')
            if not preview_thumbnail:
                raise NotFound()
            byte = app.fs.get(preview_thumbnail.get('storage_id'))
        else:
            schema = check_request_schema_validity(request.args.to_dict(), self.SCHEME_THUMBNAIL, allow_unknown=True)
            index = schema['index']
            thumbnails = next(iter(doc['thumbnails'].values()), [])
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
