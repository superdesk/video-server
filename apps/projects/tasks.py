import os
from lib.celery_app import celery
from lib.utils import format_id

from bson import json_util
from flask import current_app as app
from lib.video_editor import get_video_editor

import logging

logger = logging.getLogger(__name__)


@celery.task
def get_list_thumbnails(sdoc):
    update_thumbnails = []
    try:
        doc = json_util.loads(sdoc)
        app.mongo.db.projects.update_one({'_id': format_id(doc.get('_id'))},
                                         {"$set": {'processing': True}},
                                         upsert=False)
        file_path = '%s/%s' % (doc.get('folder'), doc.get('filename'))
        stream_file = app.fs.get(file_path)
        video_editor = get_video_editor()
        count = 0
        amount = app.config.get('AMOUNT_FRAMES', 40)
        update_thumbnails = []
        for thumbnail_stream, thumbnail_meta in video_editor.capture_list_timeline_thumnails(stream_file,
                                                                                             doc.get('filename'),
                                                                                             doc.get('metadata'),
                                                                                             amount):
            thumbnail_path = '%s_timeline_%0d.png' % (file_path, count)
            app.fs.put(thumbnail_stream, thumbnail_path)
            update_thumbnails.append(
                {
                    'filename': '%s_timeline_%0d.png' % (doc.get('filename'), count),
                    'folder': doc.get('folder'),
                    'mimetype': 'image/bmp',
                    'width': thumbnail_meta.get('width'),
                    'height': thumbnail_meta.get('height'),
                    'size': thumbnail_meta.get('size')
                }
            )
            count += 1

        app.mongo.db.projects.update_one({'_id': format_id(doc.get('_id'))},
                                         {"$set": {'thumbnails': {str(amount): update_thumbnails},
                                                   'processing': True}},
                                         upsert=False)
    except Exception as exc:
        logger.exception(exc)
        if update_thumbnails:
            for thumbnail in update_thumbnails:
                os.remove('%s/%s' % (thumbnail.get('folder'), thumbnail.get('filename')))

    return
