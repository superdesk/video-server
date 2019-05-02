import logging
import os

from bson import json_util
from flask import current_app as app
from pymongo import ReturnDocument

from lib.celery_app import celery
from lib.utils import format_id
from lib.video_editor import get_video_editor

logger = logging.getLogger(__name__)


@celery.task
def task_edit_video(temp_path, doc, updates):
    with open(temp_path, 'rb') as f:
        video_stream = f.read()
    doc = json_util.loads(doc)
    app.mongo.db.projects.update_one(
        {'_id': doc['_id']},
        {'$set': {
            'processing': True,
        }}
    )

    video_editor = get_video_editor()
    edited_video_stream, metadata = video_editor.edit_video(
        video_stream,
        doc['filename'],
        doc.get('metadata'),
        updates.get('cut'),
        updates.get('crop'),
        updates.get('rotate'),
        updates.get('quality')
    )

    app.fs.put(
        edited_video_stream,
        f"{doc['folder']}/{doc['filename']}"
    )

    updated_doc = app.mongo.db.projects.find_one_and_update(
        {'_id': doc['_id']},
        {'$set': {
            **doc,
            'processing': False,
            'metadata': metadata,
            'thumbnails': {},
        }},
        return_document=ReturnDocument.AFTER
    )
    get_list_thumbnails.delay(json_util.dumps(updated_doc))


@celery.task
def get_list_thumbnails(sdoc):
    update_thumbnails = []
    try:
        doc = json_util.loads(sdoc)
        app.mongo.db.projects.update_one(
            {'_id': format_id(doc.get('_id'))},
            {"$set": {
                'processing': True,
            }},
            upsert=False
        )

        file_path = '%s/%s' % (doc.get('folder'), doc.get('filename'))
        stream_file = app.fs.get(file_path)
        video_editor = get_video_editor()
        count = 0
        amount = app.config.get('AMOUNT_FRAMES', 40)
        for thumbnail_stream, thumbnail_meta in video_editor.capture_list_timeline_thumnails(stream_file,
                                                                                             doc.get('filename'),
                                                                                             doc.get('metadata'),
                                                                                             amount):
            thumbnail_path = '%s_timeline_%02d.png' % (file_path, count)
            app.fs.put(thumbnail_stream, thumbnail_path)
            filename, ext = os.path.splitext(doc.get('filename'))
            update_thumbnails.append(
                {
                    'filename': '%s_timeline_%0d.png' % (filename, count),
                    'folder': doc.get('folder'),
                    'mimetype': 'image/bmp',
                    'width': thumbnail_meta.get('width'),
                    'height': thumbnail_meta.get('height'),
                    'size': thumbnail_meta.get('size'),

                }
            )
            count += 1

        updates = app.mongo.db.projects.update_one(
            {'_id': format_id(doc.get('_id'))},
            {"$set": {
                'thumbnails': {
                    str(amount): update_thumbnails
                },
                'processing': False,
            }},
            upsert=False)
    except Exception as exc:
        logger.exception(exc)

        if update_thumbnails:
            for thumbnail in update_thumbnails:
                os.remove('%s/%s' % (thumbnail.get('folder'), thumbnail.get('filename')))