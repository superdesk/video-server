from datetime import datetime

from bson import json_util
from flask import current_app as app, request, Response
from flask.views import MethodView

from lib.video_editor import get_video_editor
from lib.utils import create_file_name, format_id
from lib.errors import bad_request, not_found, forbidden
from lib.validator import Validator
from . import bp


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
            return forbidden("Can store file")
        return Response(json_util.dumps(doc), status=201, mimetype='application/json')


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
        item = app.mongo.db.projects.find_one({'_id': format_id(project_id)})
        if not item:
            return not_found("Project with id: {} was not found.".format(project_id))

        return Response(json_util.dumps(item), status=200, mimetype='application/json')

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
        self._edit_video()
        return 'edited successfully'

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

        item = app.mongo.db.projects.find_one({'_id': format_id(project_id)})
        if not item:
            return not_found("Project with id: {} was not found.".format(project_id))

        self._edit_video()
        return 'edited successfully'

    def _edit_video(self):
        pass

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

        item = app.mongo.db.projects.find_one({'_id': format_id(project_id)})
        if not item:
            return not_found("Project with id: {} was not found.".format(project_id))
        app.fs.delete(f"{item.get('folder')}/{item.get('filename')}")
        app.mongo.db.projects.delete_one({'_id': format_id(project_id)})
        return 'delete successfully'


# register all urls
bp.add_url_rule('/', view_func=UploadProject.as_view('upload_project'))
bp.add_url_rule('/<path:project_id>', view_func=RetrieveEditDestroyProject.as_view('retrieve_edit_destroy_project'))
