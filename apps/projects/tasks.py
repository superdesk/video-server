import logging

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
            self.retry(max_retries=app.config.get('MAX_RETRIES', 3))
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

    try:
        thumbnails_generator = video_editor.capture_timeline_thumbnails(
            stream_file=app.fs.get(project['storage_id']),
            filename=project['filename'],
            duration=project['metadata']['duration'],
            thumbnails_amount=amount)

        for count, (stream, meta) in enumerate(thumbnails_generator, 1):
            filename = f"{project['filename'].rsplit('.', 1)[0]}_timeline_{count}-{amount}.png"
            # save to storage
            storage_id = app.fs.put(
                content=stream,
                filename=filename,
                project_id=None,
                asset_type='thumbnails',
                storage_id=project['storage_id'],
                content_type='image/png'
            )
            timeline_thumbnails.append(
                {
                    'filename': filename,
                    'storage_id': storage_id,
                    'mimetype': meta.get('mimetype')[0],
                    'width': meta.get('width'),
                    'height': meta.get('height'),
                    'size': meta.get('size')
                }
            )
        logger.info(f"Created and saved {len(timeline_thumbnails)} thumbnails to {app.fs.__class__.__name__} "
                    f"in project {project.get('_id')}.")
    except Exception as e:
        # delete just saved files
        for thumbnail in timeline_thumbnails:
            app.fs.delete(thumbnail.get('storage_id'))
        logger.info(f"Due to exception, {len(timeline_thumbnails)} just created thumbnails were removed from "
                    f"{app.fs.__class__.__name__} in project {project.get('_id')}")
        logger.exception(e)

        try:
            raise self.retry(max_retries=app.config.get('MAX_RETRIES', 3))
        except MaxRetriesExceededError:
            app.mongo.db.projects.update_one(
                {'_id': ObjectId(project.get('_id'))},
                {"$set": {
                    'processing.thumbnails_timeline': False,
                }},
                upsert=False
            )
    else:
        # remove an old thumbnails from a storage only if new thumbnails were created succesfully
        old_timeline_thumbnails = project['thumbnails'].get('timeline', [])
        for old_thumbnail in old_timeline_thumbnails:
            app.fs.delete(old_thumbnail.get('storage_id'))
        logger.info(f"Removed {len(old_timeline_thumbnails)} old thumbnails from {app.fs.__class__.__name__} "
                    f"in project {project.get('_id')}")

        # replace thumbnails in db
        app.mongo.db.projects.update_one(
            {'_id': ObjectId(project.get('_id'))},
            {"$set": {
                'thumbnails.timeline': timeline_thumbnails,
                'processing.thumbnails_timeline': False,
            }},
            upsert=False
        )
        logger.info(f"Set timeline thumbnails in db for project {project.get('_id')}.")


@celery.task(bind=True, default_retry_delay=10)
def generate_preview_thumbnail(self, project_json, position):
    project = json_util.loads(project_json)
    video_editor = get_video_editor()
    preview_thumbnail = None

    try:
        stream, meta = video_editor.capture_thumbnail(
            stream_file=app.fs.get(project['storage_id']),
            filename=project['filename'],
            duration=project['metadata']['duration'],
            position=position
        )
        filename = f"{project['filename'].rsplit('.', 1)[0]}_preview-{position}.png"
        # save to storage
        storage_id = app.fs.put(
            content=stream,
            filename=filename,
            project_id=None,
            asset_type='thumbnails',
            storage_id=project['storage_id'],
            content_type='image/png'
        )
        logger.info(f"Created and saved preview thumbnail at position {position} to {app.fs.__class__.__name__} "
                    f"in project {project.get('_id')}.")
        preview_thumbnail = {
            'filename': filename,
            'storage_id': storage_id,
            'mimetype': meta.get('mimetype')[0],
            'width': meta.get('width'),
            'height': meta.get('height'),
            'size': meta.get('size'),
            'position': position
        }
    except Exception as e:
        # delete just saved file
        if preview_thumbnail:
            app.fs.delete(preview_thumbnail.get('storage_id'))
            logger.info(f"Due to exception, just created preview thumbnail at position {position} was removed from "
                        f"{app.fs.__class__.__name__} in project {project.get('_id')}")
        logger.exception(e)

        try:
            raise self.retry(max_retries=app.config.get('MAX_RETRIES', 3))
        except MaxRetriesExceededError:
            app.mongo.db.projects.update_one(
                {'_id': ObjectId(project.get('_id'))},
                {"$set": {
                    'processing.thumbnail_preview': False,
                }},
                upsert=False
            )

    else:
        # remove an old preview thumbnail from a storage only after a new thumbnail was created succesfully
        if project['thumbnails']['preview']:
            app.fs.delete(project['thumbnails']['preview'].get('storage_id'))
            logger.info(f"Removed old preview thumbnail at position {project['thumbnails']['preview']['position']} "
                        f"from {app.fs.__class__.__name__} in project {project.get('_id')}")
        # set preview thumbnail in db
        app.mongo.db.projects.update_one(
            {'_id': ObjectId(project.get('_id'))},
            {"$set": {
                'thumbnails.preview': preview_thumbnail,
                'processing.thumbnail_preview': False,
            }},
            upsert=False
        )
        logger.info(f"Set preview thumbnail in db for project {project.get('_id')}.")
