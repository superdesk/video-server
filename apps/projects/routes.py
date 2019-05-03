import logging
import os
from datetime import datetime
from tempfile import gettempdir

from bson import json_util
from flask import Response
from flask import current_app as app
from flask import request, jsonify
from flask.views import MethodView

from lib.errors import bad_request, forbidden, not_found
from lib.utils import create_file_name, format_id, paginate
from lib.validator import Validator
from lib.video_editor import get_video_editor

from . import bp
from .tasks import get_list_thumbnails, task_edit_video

logger = logging.getLogger(__name__)


class UploadProject(MethodView):
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
                folder:
                  type: string
                  example: 2019/5
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
                      type: string
                      example: 300.014000
                    bit_rate:
                      type: string
                      example: 287654
                    nb_frames:
                      type: string
                      example: 7654
                    format_name:
                      type: string
                      example: mov,mp4,m4a,3gp,3g2,mj2
                    size:
                      type: string
                      example: 14567890
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: object
                  properties:
                    $date:
                      type: integer
                      example: 1556853105063
                original_filename:
                  type: string
                  example: video.mp4
                client_info:
                  type: string
                  example: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0
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
                  type: object
                  properties:
                    $oid:
                      type: string
                      example: 5cbd5acfe24f6045607e51aa
        """

        # validate request
        v = Validator(self.SCHEMA_UPLOAD)
        if not v.validate(request.files):
            return bad_request(v.errors)

        # validate user-agent
        user_agent = request.headers.environ['HTTP_USER_AGENT']
        client_name = user_agent.split('/')[0]
        if client_name.lower() not in app.config.get('AGENT_ALLOW'):
            return bad_request("client is not allow to edit")

        # validate codec
        video_editor = get_video_editor()
        file = request.files['file']
        file_stream = file.stream.read()
        metadata = video_editor.get_meta(file_stream)
        codec_name = metadata.get('codec_name')
        if codec_name not in app.config.get('CODEC_SUPPORT'):
            return bad_request("Codec: {} is not supported.".format(codec_name))

        # put file into storage
        file_name = create_file_name(ext=file.filename.split('.')[1])
        mime_type = file.mimetype

        # get path group by year month
        create_date = datetime.utcnow()
        folder = f'{create_date.year}/{create_date.month}'

        # put stream file into storage
        if app.fs.put(file_stream, f'{folder}/{file_name}'):
            try:
                # add record to database
                doc = {
                    'filename': file_name,
                    'folder': folder,
                    'metadata': metadata,
                    'create_date': create_date,
                    'mime_type': mime_type,
                    'version': 1,
                    'processing': False,
                    'parent': None,
                    'thumbnails': {},
                    'client_info': user_agent,
                    'original_filename': file.filename
                }
                app.mongo.db.projects.insert_one(doc)
                activity = {
                    "action": "UPLOAD",
                    "file_id": doc.get('_id'),
                    "payload": {"file": doc.get(file.filename)},
                    "create_date": create_date
                }
                app.mongo.db.activity.insert_one(activity)
            except Exception as ex:
                app.fs.delete(file_name)
                return forbidden("Can not connect database")
        else:
            return forbidden("Can not store file")
        # Run get list thumbnail for video in celery
        res = json_util.dumps(doc)
        get_list_thumbnails.delay(res)
        return Response(res, status=201, mimetype='application/json')

    def get(self):
        """
        Get list of projects in DB
        ---
        parameters:
        - name: offset
          in: query
          type: integer
          description: Page number
        - name: size
          in: query
          type: integer
          description: Number of items per page
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
                      folder:
                        type: string
                        example: 2019/5
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
                            type: string
                            example: 300.014000
                          bit_rate:
                            type: string
                            example: 287654
                          nb_frames:
                            type: string
                            example: 7654
                          format_name:
                            type: string
                            example: mov,mp4,m4a,3gp,3g2,mj2
                          size:
                            type: string
                            example: 14567890
                      mime_type:
                        type: string
                        example: video/mp4
                      create_time:
                        type: object
                        properties:
                          $date:
                            type: integer
                            example: 1556853105063
                      original_filename:
                        type: string
                        example: video.mp4
                      client_info:
                        type: string
                        example: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0
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
                        type: object
                        properties:
                          $oid:
                            type: string
                            example: 5cbd5acfe24f6045607e51aa
        """
        offset = int(request.args.get('offset', 0))
        size = int(request.args.get('size', 25))
        docs = list(app.mongo.db.projects.find())
        list_pages = list(paginate(docs, size))
        if offset >= len(list_pages):
            offset = len(list_pages) - 1
        res = {
            'items': list_pages[offset],
            'offset': offset,
            'size': len(list_pages[offset]),
            'max_size': size
        }
        return Response(json_util.dumps(res), status=200, mimetype='application/json')
        pass


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
                'start': {'type': 'integer', 'required': True},
                'end': {'type': 'integer', 'required': True},
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
                'width': {'type': 'integer', 'required': True},
                'height': {'type': 'integer', 'required': True},
                'x': {'type': 'integer', 'required': True},
                'y': {'type': 'integer', 'required': True}
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
                folder:
                  type: string
                  example: 2019/5
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
                      type: string
                      example: 300.014000
                    bit_rate:
                      type: string
                      example: 287654
                    nb_frames:
                      type: string
                      example: 7654
                    format_name:
                      type: string
                      example: mov,mp4,m4a,3gp,3g2,mj2
                    size:
                      type: string
                      example: 14567890
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: object
                  properties:
                    $date:
                      type: integer
                      example: 1556853105063
                original_filename:
                  type: string
                  example: video.mp4
                client_info:
                  type: string
                  example: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0
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
                  type: object
                  properties:
                    $oid:
                      type: string
                      example: 5cbd5acfe24f6045607e51aa
        """

        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})

        return Response(json_util.dumps(doc), status=200, mimetype='application/json')

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
                folder:
                  type: string
                  example: 2019/5
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
                      type: string
                      example: 300.014000
                    bit_rate:
                      type: string
                      example: 287654
                    nb_frames:
                      type: string
                      example: 7654
                    format_name:
                      type: string
                      example: mov,mp4,m4a,3gp,3g2,mj2
                    size:
                      type: string
                      example: 14567890
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: object
                  properties:
                    $date:
                      type: integer
                      example: 1556853105063
                original_filename:
                  type: string
                  example: video.mp4
                client_info:
                  type: string
                  example: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0
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
                  type: object
                  properties:
                    $oid:
                      type: string
                      example: 5cbd5acfe24f6045607e51aa
        """
        user_agent = self._check_user_agent()
        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})
        if doc.get('processing') is True:
            return forbidden('this video is still processing, please wait.')
        self._edit_video(doc['filename'], doc)
        activity = {
            "action": "EDIT PUT",
            "file_id": doc.get('_id'),
            "payload": {request.get_json()},
            "create_date": datetime.utcnow()
        }
        app.mongo.db.activity.insert_one(activity)
        return Response(
            json_util.dumps(doc), status=200, mimetype='application/json'
        )

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
                folder:
                  type: string
                  example: 2019/5
                metadata:
                  type: object
                  example: {}
                mime_type:
                  type: string
                  example: video/mp4
                create_time:
                  type: object
                  properties:
                    $date:
                      type: integer
                      example: 1556853105063
                original_filename:
                  type: string
                  example: video.mp4
                client_info:
                  type: string
                  example: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0
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
                  type: object
                  properties:
                    $oid:
                      type: string
                      example: 5cbd5acfe24f6045607e51aa
        """
        user_agent = self._check_user_agent()
        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})
        if doc.get('processing') is True:
            return forbidden('this video is still processing, please wait.')
        filename, ext = os.path.splitext(doc['filename'])
        version = doc.get('version', 1) + 1
        new_file_name = f'{filename}_v{version}{ext}'
        if doc.get('version') >= 2:
            return bad_request("Only POST original video version 1")

        new_doc = {
            'filename': new_file_name,
            'folder': doc['folder'],
            'metadata': None,
            'client_info': user_agent,
            'version': version,
            'processing': False,
            'mime_type': doc['mime_type'],
            'parent': {
                '_id': doc['_id'],
            },
            'thumbnails': {}
        }
        app.mongo.db.projects.insert_one(new_doc)

        self._edit_video(doc['filename'], new_doc)
        activity = {
            "action": "EDIT POST",
            "file_id": doc.get('_id'),
            "payload": {request.get_json()},
            "create_date": datetime.utcnow()
        }
        app.mongo.db.activity.insert_one(activity)
        return Response(
            json_util.dumps(new_doc), status=200, mimetype='application/json'
        )

    def _edit_video(self, current_file_name, doc):
        updates = request.get_json()
        validator = Validator(self.SCHEMA_EDIT)
        if not validator.validate(updates):
            return bad_request(validator.errors)

        actions = updates.keys()
        supported_action = ('cut', 'crop', 'rotate')
        for action in actions:
            if action not in supported_action:
                return bad_request("Action is not supported")

        file_path = os.path.join(doc['folder'], current_file_name)

        task_edit_video.delay(file_path, json_util.dumps(doc), updates)

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
          200:
            description: OK
            schema:
              type: object
              properties:
                status:
                  type: boolean
                  example: True
                message:
                  type: string
                  example: Delete successfully
        """

        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})
        app.fs.delete(f"{doc.get('folder')}/{doc.get('filename')}")
        app.mongo.db.projects.delete_one({'_id': format_id(project_id)})
        return jsonify({
            'status': True,
            'message': 'Delete successfully'
        })

    def _check_user_agent(self):
        user_agent = request.headers.environ.get('HTTP_USER_AGENT')

        client_name = user_agent.split('/')[0]
        if client_name.lower() not in app.config.get('AGENT_ALLOW'):
            return bad_request("client is not allow to edit")
        return user_agent

"""
class UploadProject(MethodView):
    def get(self, project_id):
        doc = app.mongo.db.projects.find_one({'_id': format_id(project_id)})
        if not doc:
            return not_found("Project with id: {} was not found.".format(project_id))
        media_file = app.fs.get('%s/%s')
        if media_file:
            data = wrap_file(request.environ, media_file, buffer_size=1024 * 256)
            response = app.response_class(
                data,
                mimetype=media_file.content_type,
                direct_passthrough=True)
            response.content_length = media_file.length
            response.last_modified = media_file.upload_date
            response.set_etag(media_file.md5)
            response.cache_control.max_age = cache_for
            response.cache_control.s_max_age = cache_for
            response.cache_control.public = True
            response.make_conditional(request)
            response.headers['Content-Disposition'] = 'inline'
            return response
        raise SuperdeskApiError.notFoundError('File not found on media storage.')

        pass
"""

# register all urls
bp.add_url_rule('/', view_func=UploadProject.as_view('upload_project'))
bp.add_url_rule('/<path:project_id>', view_func=RetrieveEditDestroyProject.as_view('retrieve_edit_destroy_project'))
