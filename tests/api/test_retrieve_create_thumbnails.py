import json
from io import BytesIO
from bson import ObjectId

import pytest
from flask import url_for


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_capture_timeline_thumbnails_success(test_app, client, projects):
    project = projects[0]
    amount = 3

    with test_app.test_request_context():
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=timeline&amount={amount}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True, 'thumbnails': []}

        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '200 OK'
        assert len(resp_data['thumbnails']) == amount
        for thumbnail_data in resp_data['thumbnails']:
            assert test_app.fs.get(thumbnail_data['storage_id']).__class__ is bytes


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_capture_timeline_thumbnails_remove_old(test_app, client, projects):
    project = projects[0]
    amount = 3

    with test_app.test_request_context():
        # generate 3 timeline thumbnails
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=timeline&amount={amount}'
        client.get(url)
        # generate 4 timeline thumbnails
        amount = 4
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=timeline&amount={amount}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True, 'thumbnails': []}

        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '200 OK'
        assert len(resp_data['thumbnails']) == amount
        for thumbnail_data in resp_data['thumbnails']:
            assert test_app.fs.get(thumbnail_data['storage_id']).__class__ is bytes


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_capture_timeline_thumbnails_409_resp(test_app, client, projects):
    project = projects[0]
    amount = 3

    with test_app.test_request_context():
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=timeline&amount={amount}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True, 'thumbnails': []}

        # since we use CELERY_TASK_ALWAYS_EAGER, task will be executed immediately,
        # it means next request will return a finshed result,
        # since we want to test 409 response, we must set processing flag in db directly
        test_app.mongo.db.projects.find_one_and_update(
            {'_id': ObjectId(project['_id'])},
            {'$set': {'processing.thumbnails_timeline': True}}
        )

        resp = client.get(url)
        assert resp.status == '200 OK'
        assert resp_data == {'processing': True, 'thumbnails': []}


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_capture_preview_thumbnail_success(test_app, client, projects):
    project = projects[0]
    position = 4

    with test_app.test_request_context():
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}

        resp = client.get(
            url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '200 OK'
        assert test_app.fs.get(resp_data['thumbnails']['preview']['storage_id']).__class__ is bytes

    # postion greater than duration
    position = 20
    with test_app.test_request_context():
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}

        resp = client.get(
            url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '200 OK'
        assert test_app.fs.get(resp_data['thumbnails']['preview']['storage_id']).__class__ is bytes


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_capture_preview_thumbnail_crop_success(test_app, client, projects):
    project = projects[0]
    position = 4
    crop = "0,0,640,480"

    with test_app.test_request_context():
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}&crop={crop}'
        resp = client.get(url)
        assert resp.status == '202 ACCEPTED'

        # get details
        resp = client.get(
            url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        )
        resp_data = json.loads(resp.data)
        assert resp_data['thumbnails']['preview']['width'] == 640
        assert resp_data['thumbnails']['preview']['height'] == 480


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_capture_preview_thumbnail_crop_fail(test_app, client, projects):
    project = projects[0]
    position = 4

    with test_app.test_request_context():
        crop = "1000,0,640,480"
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}&crop={crop}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['x is less than minimum allowed crop width']}

        crop = "0,1000,640,480"
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}&crop={crop}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['y is less than minimum allowed crop height']}

        crop = "0,0,10000,480"
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}&crop={crop}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['width 10000 is greater than maximum allowed crop width (3840)']}

        crop = "0,0,640,10000"
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}&crop={crop}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ['height 10000 is greater than maximum allowed crop height (2160)']}

        crop = "0,0,1640,480"
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}&crop={crop}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ["width of crop's frame is outside a video's frame"]}

        crop = "0,0,640,1480"
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}&crop={crop}'
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': ["height of crop's frame is outside a video's frame"]}


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_capture_preview_thumbnail_409_resp(test_app, client, projects):
    project = projects[0]
    position = 700

    # since we use CELERY_TASK_ALWAYS_EAGER, task will be executed immediately,
    # it means next request will return a finshed result,
    # since we want to test 409 response, we must set processing flag in db directly
    test_app.mongo.db.projects.find_one_and_update(
        {'_id': ObjectId(project['_id'])},
        {'$set': {'processing.thumbnail_preview': True}}
    )

    with test_app.test_request_context():
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}'
        resp = client.get(url)
        assert resp.status == '409 CONFLICT'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
@pytest.mark.parametrize('filestreams', [('sample_0.jpg',)], indirect=True)
def test_upload_custom_preview_thumbnail_success(test_app, client, projects, filestreams):
    project = projects[0]
    jpg_stream = filestreams[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_or_create_thumbnails', project_id=project['_id'])
        resp = client.post(
            url,
            data={
                'file': (BytesIO(jpg_stream), 'sample_0.jpg')
            },
            content_type='multipart/form-data'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '200 OK'
        assert test_app.fs.get(resp_data['storage_id']).__class__ is bytes


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_upload_custom_preview_thumbnail_no_file(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_or_create_thumbnails', project_id=project['_id'])
        resp = client.post(
            url,
            data={},
            content_type='multipart/form-data'
        )
        assert resp.status == '400 BAD REQUEST'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_upload_custom_preview_thumbnail_wrong_codec(test_app, client, projects, filestreams):
    project = projects[0]
    jpg_stream = filestreams[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_or_create_thumbnails', project_id=project['_id'])
        resp = client.post(
            url,
            data={
                'file': (BytesIO(jpg_stream), 'sample_0.jpg')
            },
            content_type='multipart/form-data'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'file': ["Codec: 'h264' is not supported."]}


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
@pytest.mark.parametrize('filestreams', [('sample_0.jpg',)], indirect=True)
def test_upload_custom_preview_thumbnail_409_resp(test_app, client, projects, filestreams):
    project = projects[0]
    jpg_stream = filestreams[0]

    # since we use CELERY_TASK_ALWAYS_EAGER, task will be executed immediately,
    # it means next request will return a finshed result,
    # since we want to test 409 response, we must set processing flag in db directly
    test_app.mongo.db.projects.find_one_and_update(
        {'_id': ObjectId(project['_id'])},
        {'$set': {'processing.thumbnail_preview': True}}
    )

    with test_app.test_request_context():
        url = url_for('projects.retrieve_or_create_thumbnails', project_id=project['_id'])
        resp = client.post(
            url,
            data={
                'file': (BytesIO(jpg_stream), 'sample_0.jpg')
            },
            content_type='multipart/form-data'
        )
        assert resp.status == '409 CONFLICT'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
@pytest.mark.parametrize('filestreams', [('sample_0.jpg',)], indirect=True)
def test_upload_custom_preview_remove_old_thumbnail(test_app, client, projects, filestreams):
    project = projects[0]
    jpg_stream = filestreams[0]
    position = 3

    with test_app.test_request_context():
        # capture preview
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + f'?type=preview&position={position}'
        resp = client.get(url)
        assert resp.status == '202 ACCEPTED'
        # get storage_id of captured preview thumbnail
        resp = client.get(
            url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        )
        resp_data = json.loads(resp.data)
        captured_thumb_strage_id = resp_data['thumbnails']['preview']['storage_id']
        # upload custom preview thumbnail
        url = url_for('projects.retrieve_or_create_thumbnails', project_id=project['_id'])
        resp = client.post(
            url,
            data={
                'file': (BytesIO(jpg_stream), 'sample_0.jpg')
            },
            content_type='multipart/form-data'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '200 OK'
        assert test_app.fs.get(resp_data['storage_id']).__class__ is bytes
        # check that old thumbnail is deleted
        with pytest.raises(FileNotFoundError):
            test_app.fs.get(captured_thumb_strage_id)
