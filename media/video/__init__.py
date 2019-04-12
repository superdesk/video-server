"""Upload module"""
import logging
import superdesk
from bson import ObjectId
from flask import request, current_app as app, redirect
import json
from media.celery_app import add
from media.data_layer import get_collection

bp = superdesk.Blueprint('project', __name__)

METADATA = {
    "filename": "58482c53a121828cc5135de86be5257859ce586281f612d148fa853a75c6f64e",
    "metadata": {
        "length": "69211"
    },
    "contentType": "image/jpeg",
    "md5": "a4abe83c1ad2dccbd996f069765a36ed",
    "chunkSize": 261120,
    "length": 69211,
}


@bp.route('/project', methods=['POST'])
def create_video_editor():
    if request.method == 'POST':
        return create_video(request.form)


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


def create_video(doc):
    """Keep previous url for backward compatibility"""
    add.delay(doc)
    return 'insert successfully'


def get_video(video_id):
    """Keep previous url for backward compatibility"""
    video = get_collection('video')
    items = list(video.find())
    for item in items:
        item['_id'] = str(item['_id'])
    return json.dumps(items)


def init_app(app):
    superdesk.blueprint(bp, app)
