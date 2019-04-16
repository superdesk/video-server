"""Upload module"""
import logging
import superdesk
from bson import ObjectId
from flask import request
import json
from media import get_collection
from superdesk.media.media_operations import process_file_from_stream
from flask import current_app as app

bp = superdesk.Blueprint('project', __name__)


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


@bp.route('/project', methods=['POST'])
def create_video_editor():
    if request.method == 'POST':
        files = request.files.to_dict(flat=False)['media']
        user_agent = request.headers.environ['HTTP_USER_AGENT']

        return create_video(files, user_agent)


@bp.route('/project/<path:video_id>', methods=['GET', 'PUT', 'DELETE'])
def process_video_editor(video_id):
    """Keep previous url for backward compatibility"""
    if request.method == 'GET':
        return get_video(video_id)
    if request.method == 'PUT':
        return update_video(video_id, request.form)
    if request.method == 'DELETE':
        return delete_video(video_id)


def delete_video(video_id):
    video = get_collection('video')
    video.remove({'_id': ObjectId(video_id)})
    return 'delete successfully'


def update_video(video_id, updates):
    video = get_collection('video')
    updates = {"$set": {"chunkSize": 0}}
    update = video.update_one({'_id': ObjectId(video_id)}, updates)
    return 'update successfully'


def create_video(files, agent):
    """Save video to storage and create records to databases"""
    video = get_collection('video')
    docs = []
    for file in files:
        file_name, content_type, metadata = process_file_from_stream(file)
        doc = {
            'metadata': metadata,
            'client_info': agent,
            'version': 1,
            'processing': False,
            "parent": None,
            'thumbnails': {}
        }
        docs.append(doc)
    video.insert_many(docs)
    return JSONEncoder().encode(docs)


def get_video(video_id):
    """Keep previous url for backward compatibility"""
    video = get_collection('video')
    items = list(video.find())
    for item in items:
        item['_id'] = str(item['_id'])
    return items


def init_app(app):
    superdesk.blueprint(bp, app)
