import os
import json
import shutil
from io import BytesIO

import pytest
from flask import url_for

from videoserver.app import get_app


@pytest.fixture(scope='function')
def test_app(request):
    """
    Main test app fixture.

    :return: flask app
    """
    test_app = get_app()
    test_app.config['ITEMS_PER_PAGE'] = 2
    test_app.config['TESTING'] = True
    test_app.config['MONGO_DBNAME'] = 'sd_video_editor_test'
    test_app.config['MONGO_URI'] = 'mongodb://localhost:27017/sd_video_editor_test'
    test_app.config['FS_MEDIA_STORAGE_PATH'] = os.path.join(os.path.dirname(__file__), 'media', 'projects')
    test_app.config['CELERY_TASK_ALWAYS_EAGER'] = True
    test_app.config['MIN_TRIM_DURATION'] = 2

    if not os.path.exists(test_app.config['FS_MEDIA_STORAGE_PATH']):
        os.makedirs(test_app.config['FS_MEDIA_STORAGE_PATH'])

    test_app.init_db()

    def test_app_teardown():
        """
        Remove test folder and drop test db
        """
        # drop test db
        test_app.mongo.db.projects.drop()
        # drop test media folder
        if os.path.exists(test_app.config['FS_MEDIA_STORAGE_PATH']):
            shutil.rmtree(os.path.dirname(test_app.config.get('FS_MEDIA_STORAGE_PATH')))

    request.addfinalizer(test_app_teardown)

    return test_app


@pytest.fixture(scope='function')
def client(test_app):
    client = test_app.test_client()

    with test_app.app_context():
        yield client


@pytest.fixture(scope='function')
def filestreams(request):
    filestreams = []

    for filename in request.param:
        test_path = os.path.dirname(os.path.abspath(__file__))
        with open(f'{test_path}/storage/fixtures/{filename}', 'rb') as f:
            filestream = f.read()
        filestreams.append(filestream)

    return filestreams


@pytest.fixture(scope='function')
def projects(request, test_app, client):
    projects = []

    for param in request.param:
        test_path = os.path.dirname(os.path.abspath(__file__))
        with open(f'{test_path}/storage/fixtures/{param["file"]}', 'rb') as f:
            filestream = f.read()
        with test_app.test_request_context():
            # create a project
            url = url_for('projects.list_upload_project')
            resp = client.post(
                url,
                data={
                    'file': (BytesIO(filestream), param["file"])
                },
                content_type='multipart/form-data'
            )
            resp_data = json.loads(resp.data)
            # duplicate
            if param["duplicate"]:
                url = url_for('projects.duplicate_project', project_id=resp_data['_id'])
                resp = client.post(url)
                resp_data = json.loads(resp.data)

            projects.append(resp_data)

    return projects
