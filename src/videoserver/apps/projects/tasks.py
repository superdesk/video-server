import logging
from time import time

from bson import ObjectId
from celery.exceptions import MaxRetriesExceededError
from flask import current_app as app
from pymongo import ReturnDocument

from videoserver.celery_app import celery
from videoserver.lib.video_editor import get_video_editor

logger = logging.getLogger(__name__)


@celery.task(bind=True, default_retry_delay=10)
def edit_video(self, project, changes):
    """
    Task use tool for edit video and record the data and update status after finished,
    :param project: project doc
    :param changes: changes apply to the video
    """

    video_editor = get_video_editor()

    try:
        # Use tool for editing video
        edited_video_stream, metadata = video_editor.edit_video(
            stream_file=app.fs.get(project['storage_id']),
            filename=project['filename'],
            **changes
        )

        app.fs.replace(
            edited_video_stream,
            project['storage_id'],
            None
        )
        logger.info(f"Replaced file {project['storage_id']} in {app.fs.__class__.__name__} "
                    f"in project {project.get('_id')}")
    except Exception as exc:
        logger.exception(exc)
        try:
            self.retry(max_retries=app.config.get('MAX_RETRIES', 3))
        except MaxRetriesExceededError:
            app.mongo.db.projects.update_one(
                {'_id': ObjectId(project.get('_id'))},
                {"$set": {
                    'processing.video': False,
                }},
                upsert=False
            )
    else:
        # delete old timeline thumbnails
        old_timeline_thumbnails = project['thumbnails'].get('timeline', [])
        for old_thumbnail in old_timeline_thumbnails:
            app.fs.delete(old_thumbnail.get('storage_id'))
        logger.info(f"Removed {len(old_timeline_thumbnails)} old thumbnails from {app.fs.__class__.__name__} "
                    f"in project {project.get('_id')}")

        # update project record
        app.mongo.db.projects.find_one_and_update(
            {'_id': project['_id']},
            {'$set': {
                'processing.video': False,
                'metadata': metadata,
                'thumbnails.timeline': [],
                'version': project['version'] + 1
            }},
            return_document=ReturnDocument.BEFORE
        )
        logger.info(f"Finished editing for project {project.get('_id')}.")


@celery.task(bind=True, default_retry_delay=10)
def generate_timeline_thumbnails(self, project, amount):
    timeline_thumbnails = []
    video_editor = get_video_editor()

    try:
        thumbnails_generator = video_editor.capture_timeline_thumbnails(
            stream_file=app.fs.get(project['storage_id']),
            filename=project['filename'],
            duration=project['metadata']['duration'],
            thumbnails_amount=amount)

        for count, (stream, meta) in enumerate(thumbnails_generator, 1):
            ext = app.config.get('CODEC_EXTENSION_MAP')[meta.get('codec_name')]
            filename = f"{project['filename'].rsplit('.', 1)[0]}_timeline_{count}-{amount}.{ext}"
            # save to storage
            storage_id = app.fs.put(
                content=stream,
                filename=filename,
                project_id=None,
                asset_type='thumbnails',
                storage_id=project['storage_id'],
                content_type=meta.get('mimetype')
            )
            timeline_thumbnails.append(
                {
                    'filename': filename,
                    'storage_id': storage_id,
                    'mimetype': meta.get('mimetype'),
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
def generate_preview_thumbnail(self, project, position, crop, rotate):
    video_editor = get_video_editor()
    preview_thumbnail = None

    try:
        stream, meta = video_editor.capture_thumbnail(
            stream_file=app.fs.get(project['storage_id']),
            filename=project['filename'],
            duration=project['metadata']['duration'],
            position=position,
            crop=crop,
            rotate=rotate,
        )
        # Generate _id to ensure filename is unique, avoid fs.put raises error,
        # use of fs.replace will lead to lost original thumbnail if an error is occured
        _id = round(time() * 1000)
        ext = app.config.get('CODEC_EXTENSION_MAP')[meta.get('codec_name')]
        filename = f"{project['filename'].rsplit('.', 1)[0]}_preview-{position}_{_id}.{ext}"
        # save to storage
        storage_id = app.fs.put(
            content=stream,
            filename=filename,
            project_id=None,
            asset_type='thumbnails',
            storage_id=project['storage_id'],
            content_type=meta.get('mimetype')
        )
        logger.info(f"Created and saved preview thumbnail at position {position} to {app.fs.__class__.__name__} "
                    f"in project {project.get('_id')}.")
        preview_thumbnail = {
            'filename': filename,
            'storage_id': storage_id,
            'mimetype': meta.get('mimetype'),
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
