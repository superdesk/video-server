import logging
import os
from datetime import datetime
from tempfile import gettempdir

from bson import json_util
from flask import Response
from flask import current_app as app
from flask import request
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
        parameters:
        - in: body
          name: body
          description: file object to upload
          schema:
            type: object
            required:
              file
            properties:
              file:
                type: binary
        responses:
          '201':
            description: CREATED
            schema:
              type: object
              properties:
                filename:
                  type: string
                  example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                metadata:
                  type: object
                  example: {...}
                client_info:
                  type: string
                  example: PostmanRuntime/7.6.0
                version:
                  type: integer
                  example: 1
                parent:
                  type: object
                  example: {}
                thumbnails:
                  type: object
                  example: {}
                _id:
                  type: object
                  schema:
                    type: object
                    properties:
                      $oid:
                        type: string
                  example: { $oid: 5cbd5acfe24f6045607e51aa}

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
                    'create_time': create_date,
                    'mime_type': mime_type,
                    'version': 1,
                    'processing': False,
                    'parent': None,
                    'thumbnails': {},
                    'client_info': user_agent,
                    'original_filename': file.filename
                }
                app.mongo.db.projects.insert_one(doc)
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
          '200':
            description: OK
            schema:
              type: object
              properties:
                _id:
                  type: object
                  schema:
                    type: object
                    properties:
                      $oid:
                        type: string
                  example: { $oid: 5cbd5acfe24f6045607e51aa}
                filename:
                  type: string
                  example: fa5079a38e0a4197864aa2ccb07f3bea.mp4
                metadata:
                  type: object
                  example: {...}
                client_info:
                  type: string
                  example: PostmanRuntime/7.6.0
                version:
                  type: integer
                  example: 1
                parent:
                  type: object
                  example: {}
                thumbnails:
                  type: object
                  example: {}
        """

        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})

        return Response(json_util.dumps(doc), status=200, mimetype='application/json')

    def put(self, project_id):
        """
        Edit video. This method does not create a new project.
        ---
        parameters:
            - name: project_id
              in: path
              type: string
              required: true
              description: Unique project id
        """
        client_name = self._check_user_agent()
        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})
        self._edit_video(doc['filename'], doc)
        return Response(
            json_util.dumps(doc), status=200, mimetype='application/json'
        )

    def post(self, project_id):
        """
        Edit video. This method creates a new project.
        ---
        parameters:
            - name: project_id
              in: path
              type: string
              required: true
              description: Unique project id
        """
        client_name = self._check_user_agent()
        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})

        filename, ext = os.path.splitext(doc['filename'])
        version = doc.get('version', 1) + 1
        new_file_name = f'{filename}_v{version}{ext}'

        new_doc = {
            'filename': new_file_name,
            'folder': doc['folder'],
            'metadata': None,
            'client_info': client_name,
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
        temp_path = os.path.join(gettempdir(), file_path)
        temp_dir = os.path.dirname(temp_path)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        video_stream = app.fs.get(file_path)
        with open(temp_path, 'wb') as f:
            f.write(video_stream)

        task_edit_video.delay(temp_path, json_util.dumps(doc), updates)

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
        """

        doc = app.mongo.db.projects.find_one_or_404({'_id': format_id(project_id)})
        app.fs.delete(f"{doc.get('folder')}/{doc.get('filename')}")
        app.mongo.db.projects.delete_one({'_id': format_id(project_id)})
        return 'delete successfully'

    def _check_user_agent(self):
        user_agent = request.headers.environ.get('HTTP_USER_AGENT')

        client_name = user_agent.split('/')[0]
        if client_name.lower() not in app.config.get('AGENT_ALLOW'):
            return bad_request("client is not allow to edit")


# register all urls
bp.add_url_rule('/', view_func=UploadProject.as_view('upload_project'))
bp.add_url_rule('/<path:project_id>', view_func=RetrieveEditDestroyProject.as_view('retrieve_edit_destroy_project'))
