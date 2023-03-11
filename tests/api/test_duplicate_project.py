import json
from bson import ObjectId
from unittest import mock

import pytest
from flask import url_for
from pymongo.errors import ServerSelectionTimeoutError


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_duplicate_project_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.duplicate_project', project_id=project['_id'])
        resp = client.post(url)
        resp_data = json.loads(resp.data)

        assert resp.status == '201 CREATED'
        assert '_id' in resp_data
        assert 'filename' in resp_data
        assert 'storage_id' in resp_data
        assert 'create_time' in resp_data
        assert resp_data['mime_type'] == 'video/mp4'
        assert resp_data['request_address'] == '127.0.0.1'
        assert resp_data['original_filename'] == project['original_filename']
        assert resp_data['version'] == 2
        assert resp_data['parent'] == project['_id']
        assert resp_data['processing'] == {'video': False, 'thumbnail_preview': False, 'thumbnails_timeline': False}
        assert resp_data['thumbnails'] == {'timeline': [], 'preview': {}}
        assert resp_data['url'] == url_for('projects.get_raw_video', project_id=resp_data["_id"], _external=True)
        assert resp_data['metadata']['codec_name'] == 'h264'
        assert resp_data['metadata']['codec_long_name'] == 'H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10'
        assert resp_data['metadata']['width'] == 1280
        assert resp_data['metadata']['height'] == 720
        assert resp_data['metadata']['r_frame_rate'] == '25/1'
        assert resp_data['metadata']['bit_rate'] == 1045818
        assert resp_data['metadata']['nb_frames'] == 375
        assert resp_data['metadata']['duration'] == 15.0
        assert resp_data['metadata']['format_name'] == 'mov,mp4,m4a,3gp,3g2,mj2'
        assert 'size' in resp_data['metadata']


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
@mock.patch('videoserver.apps.projects.routes.app.fs.put', side_effect=Exception('Some error'))
def test_duplicate_project_broken_fs_put(mock_fs_put, test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.duplicate_project', project_id=project['_id'])
        resp = client.post(url)
        resp_data = json.loads(resp.data)

        assert resp.status == '500 INTERNAL SERVER ERROR'
        assert resp_data == {'error': 'Some error'}
        assert list(test_app.mongo.db.projects.find()).__len__() == 1


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_duplicate_project_409_resp(test_app, client, projects):
    project = projects[0]

    # since we use CELERY_TASK_ALWAYS_EAGER, task will be executed immediately,
    # it means next request will return a finshed result,
    # since we want to test 409 response, we must set processing flag in db directly
    test_app.mongo.db.projects.find_one_and_update(
        {'_id': ObjectId(project['_id'])},
        {'$set': {'processing.video': True}}
    )

    with test_app.test_request_context():
        url = url_for('projects.duplicate_project', project_id=project['_id'])
        resp = client.post(url)

        assert resp.status == '409 CONFLICT'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_duplicate_project_with_thumbnails(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # capture preview thumbnail
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + '?type=preview&position=3'
        resp = client.get(url)
        assert resp.status == '202 ACCEPTED'
        # capture timeline thumbnails
        amount = 3
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=timeline&amount={amount}'
        resp = client.get(url)
        assert resp.status == '202 ACCEPTED'
        # duplicate
        url = url_for('projects.duplicate_project', project_id=project['_id'])
        resp = client.post(url)
        resp_data = json.loads(resp.data)

        assert resp.status == '201 CREATED'
        assert resp_data['thumbnails']['preview'] is not None
        assert test_app.fs.get(resp_data['thumbnails']['preview']['storage_id']).__class__ is bytes
        assert len(resp_data['thumbnails']['timeline']) == amount
        for thumbn_data in resp_data['thumbnails']['timeline']:
            assert test_app.fs.get(thumbn_data['storage_id']).__class__ is bytes


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
@mock.patch('pymongo.collection.Collection.find_one_and_update',
            side_effect=ServerSelectionTimeoutError('Timeout error'))
def test_duplicate_project_cant_set_storage_id(mock_find_one_and_update, test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # duplicate
        url = url_for('projects.duplicate_project', project_id=project['_id'])
        resp = client.post(url)
        resp_data = json.loads(resp.data)

        assert resp.status == '500 INTERNAL SERVER ERROR'
        assert resp_data == {'error': 'Timeout error'}
        assert len(list(test_app.mongo.db.projects.find())) == len(projects)
