from bson import ObjectId, json_util
from flask import Blueprint, Response
from flask import current_app as app
from flask import request
from werkzeug.datastructures import FileStorage

from media import get_media_collection, get_thumbnails_collection
from media.utils import create_file_name, validate_json
from media.video import get_video_editor_tool

from .errors import bad_request

bp = Blueprint('projects', __name__)

SCHEMA_UPLOAD = {'filename': {'type': 'string', 'required': True, 'empty': True}}


@bp.route('/projects', methods=['POST'])
def create_video_editor():
    """
        Api put a file into storage video server
        content-type: multipart/form-data
        payload:
            files: {'media': <file>}
            form: {filename: <string>}

        response: http 201
        {
            "filename": "fa5079a38e0a4197864aa2ccb07f3bea.mp4",
            "metadata": null,
            "client_info": "PostmanRuntime/7.6.0",
            "version": 1,
            "processing": false,
            "parent": null,
            "thumbnails": {},
            "_id": {
                "$oid": "5cbd5acfe24f6045607e51aa"
            }
        }
    :return:
    """
    if request.method == 'POST':
        files = request.files
        user_agent = request.headers.environ['HTTP_USER_AGENT']
        file_name = request.form.to_dict()
        if not validate_json(SCHEMA_UPLOAD, file_name):
            return bad_request("invalid request")
        return create_video(files, file_name.get('filename'), user_agent)


@bp.route('/projects/<path:video_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def process_video_editor(video_id):
    """Keep previous url for backward compatibility"""
    if request.method == 'GET':
        return get_video(video_id)
    if request.method == 'PUT':
        return update_video(video_id, request.form)
    if request.method == 'POST':
        return update_video(video_id, request.form)
    if request.method == 'DELETE':
        return delete_video(video_id)


def delete_video(video_id):
    video = get_media_collection()
    video.remove({'_id': format_id(video_id)})
    return 'delete successfully'


def update_video(video_id, updates):
    return 'update successfully'


def create_video(files, original_filename, agent):
    """Validate data, then save video to storage and create records to databases"""
    #: validate incoming data is a file
    if 'media' not in files or not isinstance(files.get('media'), FileStorage):
        return bad_request("file can not found in 'media'")

    #: validate the user agent must be in a list support
    client_name = agent.split('/')[0]
    if client_name.lower() not in app.config.get('AGENT_ALLOW'):
        return bad_request("client is not allow to edit")

    video_editor = get_video_editor_tool('ffmpeg')
    file = files.get('media')
    file_stream = file.stream.read()
    metadata = video_editor.get_meta(file_stream)
    #: validate codec must be support
    if metadata.get('codec_name') not in app.config.get('CODEC_SUPPORT'):
        return bad_request("codec is not support")

    ext = file.filename.split('.')[1]
    file_name = create_file_name(ext)
    #: put file into storage
    doc = app.fs.put(None, file_stream, file_name, metadata=metadata, client_info=agent,
                     original_filename=original_filename)
    thumbnails = []
    for thumbnail_id in doc['thumbnails']:
        thumbnail = (
            get_thumbnails_collection()
                .find_one({'_id': format_id(thumbnail_id)})
        )
        thumbnails.append(thumbnail)
    doc['thumbnails'] = json_util.dumps(thumbnails)
    return Response(json_util.dumps(doc), status=201, mimetype='application/json')


def get_video(video_id):
    """Get data media"""
    media = get_media_collection()
    items = list(media.find({'_id': format_id(video_id)}))
    for item in items:
        item['_id'] = str(item['_id'])
    return Response(json_util.dumps(items), status=200, mimetype='application/json')


def format_id(_id):
    try:
        return ObjectId(_id)
    except Exception as ex:
        return None
