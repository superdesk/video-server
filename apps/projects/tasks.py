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
def task_edit_video(sdoc, updates, action='post', retry=0):
    """
    Task use tool for edit video and record the data and update status after finished,
    :param file_path: full path edit video
    :param sdoc: type json string, data info edit video
    :param updates: type dictionary, changes apply to the video
    :param action: put/replace action for new edited video
    :param retry:
    :return:
    """
    doc = json_util.loads(sdoc)
    storage_id = doc['storage_id']
    try:
        video_stream = app.fs.get(doc['storage_id'])

        # Use tool for editing video
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
        if action == 'post':
            new_storage_id = app.fs.put(edited_video_stream, doc.get('filename'), None)
        elif action == 'put':
            new_storage_id = app.fs.replace(edited_video_stream, storage_id, None)
        else:
            raise KeyError(f'Invalid action `{action}`')

        # create url for preview video
        url = app.fs.url_for_media(doc.get('_id'))
        # Update data status is True and data video when edit was finished
        app.mongo.db.projects.find_one_and_update(
            {'_id': doc['_id']},
            {'$set': {
                'processing': False,
                'metadata': metadata,
                'storage_id': new_storage_id,
                'thumbnails': {},
                'url': url
            }},
            return_document=ReturnDocument.AFTER
        )
        # Delete all old thumbnails
        thumbnails = []
        for key in doc['thumbnails'].keys():
            thumbnails = doc['thumbnails'][str(key)]
        for thumbnail in thumbnails:
            app.fs.delete(thumbnail['storage_id'])

    except Exception as exc:
        logger.exception(exc)
        if retry < app.config.get('NUMBER_RETRY', 3):
            task_edit_video.delay(json_util.dumps(doc), updates, action, retry=retry + 1)
        else:
            if doc['version'] >= 2:
                app.mongo.db.projects.delete_one({'_id': doc['_id']})
            else:
                app.mongo.db.projects.update_one(
                    {'_id': doc['_id']},
                    {'$set': {
                        'processing': False,
                    }}
                )


@celery.task
def task_get_list_thumbnails(sdoc, amount, retry=0):
    update_thumbnails = []
    try:
        doc = json_util.loads(sdoc)

        # get full path file of video
        filename, ext = os.path.splitext(doc['filename'])
        stream_file = app.fs.get(doc['storage_id'])
        video_editor = get_video_editor()
        count = 0
        for thumbnail_stream, \
            thumbnail_meta in video_editor.capture_list_timeline_thumbnails(stream_file,
                                                                            filename,
                                                                            doc.get('metadata'),
                                                                            int(amount)):
            thumbnail_filename = '%s_timeline_%02d.png' % (filename, count)
            storage_id = app.fs.put(thumbnail_stream, thumbnail_filename, 'image/png')
            update_thumbnails.append(
                {
                    'filename': '%s_timeline_%02d.png' % (filename, count),
                    'storage_id': storage_id,
                    'mimetype': 'image/png',
                    'width': thumbnail_meta.get('width'),
                    'height': thumbnail_meta.get('height'),
                    'size': thumbnail_meta.get('size'),
                    'url': f"{app.fs.url_for_media(doc.get('_id'))}?thumbnail={count}"

                }
            )
            count += 1
        # Update data status is True and data video when getting thumbnails was finished.
        app.mongo.db.projects.update_one(
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
                path_thumbnail = os.path.join(app.config.get('FS_MEDIA_STORAGE_PATH'),
                                              thumbnail.get('folder'), thumbnail.get('filename'))
                if os.path.exists(path_thumbnail):
                    os.remove(path_thumbnail)
        if retry < app.config.get('NUMBER_RETRY', 3):
            task_get_list_thumbnails.delay(sdoc, retry=retry + 1)
        else:
            app.mongo.db.projects.update_one(
                {'_id': format_id(doc.get('_id'))},
                {"$set": {
                    'processing': True,
                }},
                upsert=False)
