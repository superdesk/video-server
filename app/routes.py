from bson import ObjectId
from flask import request, Response
from media import get_collection
from flask import Blueprint
from bson import json_util

bp = Blueprint('projects', __name__)


@bp.route('/projects', methods=['POST'])
def create_video_editor():
    if request.method == 'POST':
        files = request.files.to_dict(flat=False)['media']
        user_agent = request.headers.environ['HTTP_USER_AGENT']

        return create_video(files, user_agent)


@bp.route('/projects/<path:video_id>', methods=['GET', 'PUT', 'DELETE'])
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
        doc = {
            'metadata': None,
            'client_info': agent,
            'version': 1,
            'processing': False,
            "parent": None,
            'thumbnails': {}
        }
        docs.append(doc)
    video.insert_many(docs)

    return Response(json_util.dumps(docs), status=200, mimetype='application/json')


def get_video(video_id):
    """Keep previous url for backward compatibility"""
    video = get_collection('video')
    items = list(video.find())
    for item in items:
        item['_id'] = str(item['_id'])
    return items
