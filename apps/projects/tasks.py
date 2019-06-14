import logging
import os

from bson import json_util, ObjectId
from flask import current_app as app
from pymongo import ReturnDocument

from celery.exceptions import MaxRetriesExceededError
from lib.utils import get_url_for_media, create_temp_file
from lib.video_editor import get_video_editor

from celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(bind=True, default_retry_delay=10)
def task_edit_video(self, sdoc, updates, action='post'):
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
            new_storage_id = app.fs.put(
                edited_video_stream, doc.get('filename'),
                project_id=None, asset_type='thumbnails', storage_id=storage_id, content_type=None)
        elif action == 'put':
            new_storage_id = app.fs.replace(edited_video_stream, storage_id, None)
        else:
            raise KeyError(f'Invalid action `{action}`')

        # create url for preview video
        url = get_url_for_media(doc.get('_id'), 'video')
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
        for thumbnail in next(iter(doc['thumbnails'].values()), []):
            app.fs.delete(thumbnail['storage_id'])

    except Exception as exc:
        logger.exception(exc)
        try:
            self.retry(max_retries=app.config.get('NUMBER_RETRY', 3))
        except MaxRetriesExceededError:
            if doc['version'] >= 2:
                app.mongo.db.projects.delete_one({'_id': doc['_id']})
            else:
                app.mongo.db.projects.update_one(
                    {'_id': doc['_id']},
                    {'$set': {
                        'processing': False,
                    }}
                )


@celery.task(bind=True, default_retry_delay=10)
def generate_timeline_thumbnails(self, project_json, amount):
    project = json_util.loads(project_json)
    timeline_thumbnails = []
    video_editor = get_video_editor()

    video_editor.capture_timeline_thumbnails(
        stream_file=app.fs.get(project['storage_id']),
        filename=project['filename'],
        duration=float(project['metadata']['duration']),
        thumbnails_amount=amount
    )



    # count = 0
    # for thumbnail_stream, thumbnail_meta in video_editor.capture_list_timeline_thumbnails(stream_file,
    #                                                                     filename,
    #                                                                     project.get('metadata'),
    #                                                                     int(amount)):
    #     thumbnail_filename = '%s_timeline_%02d.png' % (filename, count)
    #     storage_id = app.fs.put(
    #         thumbnail_stream, thumbnail_filename, None,
    #         asset_type='thumbnails', storage_id=project['storage_id'], content_type='image/png')
    #     timeline_thumbnails.append(
    #         {
    #             'filename': '%s_timeline_%02d.png' % (filename, count),
    #             'storage_id': storage_id,
    #             'mimetype': 'image/png',
    #             'width': thumbnail_meta.get('width'),
    #             'height': thumbnail_meta.get('height'),
    #             'size': thumbnail_meta.get('size'),
    #             'url': get_url_for_media(project.get('_id'), 'thumbnail') + f'?index={count}'
    #         }
    #     )
    #     count += 1
    # # Update data status is True and data video when getting thumbnails was finished.
    # app.mongo.db.projects.update_one(
    #     {'_id': ObjectId(project.get('_id'))},
    #     {"$set": {
    #         'thumbnails': {
    #             str(amount): timeline_thumbnails
    #         },
    #         'processing': False,
    #     }},
    #     upsert=False)



    # try:
    #     project = json_util.loads(project_json)
    #
    #     # get full path file of video
    #     filename, ext = os.path.splitext(project['filename'])
    #     stream_file = app.fs.get(project['storage_id'])
    #     video_editor = get_video_editor()
    #     count = 0
    #     for thumbnail_stream, \
    #         thumbnail_meta in video_editor.capture_list_timeline_thumbnails(stream_file,
    #                                                                         filename,
    #                                                                         project.get('metadata'),
    #                                                                         int(amount)):
    #         thumbnail_filename = '%s_timeline_%02d.png' % (filename, count)
    #         storage_id = app.fs.put(
    #             thumbnail_stream, thumbnail_filename, None,
    #             asset_type='thumbnails', storage_id=project['storage_id'], content_type='image/png')
    #         update_thumbnails.append(
    #             {
    #                 'filename': '%s_timeline_%02d.png' % (filename, count),
    #                 'storage_id': storage_id,
    #                 'mimetype': 'image/png',
    #                 'width': thumbnail_meta.get('width'),
    #                 'height': thumbnail_meta.get('height'),
    #                 'size': thumbnail_meta.get('size'),
    #                 'url': get_url_for_media(project.get('_id'), 'thumbnail') + f'?index={count}'
    #             }
    #         )
    #         count += 1
    #     # Update data status is True and data video when getting thumbnails was finished.
    #     app.mongo.db.projects.update_one(
    #         {'_id': ObjectId(project.get('_id'))},
    #         {"$set": {
    #             'thumbnails': {
    #                 str(amount): update_thumbnails
    #             },
    #             'processing': False,
    #         }},
    #         upsert=False)
    # except Exception as exc:
    #     logger.exception(exc)
    #     # if update_thumbnails:
    #     #     for thumbnail in update_thumbnails:
    #     #         app.fs.delete(thumbnail.get('storage_id'))
    #     # try:
    #     #     raise self.retry(max_retries=app.config.get('NUMBER_RETRY', 3))
    #     # except MaxRetriesExceededError:
    #     #     app.mongo.db.projects.update_one(
    #     #         {'_id': ObjectId(project.get('_id'))},
    #     #         {"$set": {
    #     #             'processing': False,
    #     #         }},
    #     #         upsert=False)
