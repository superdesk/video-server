import json
from bson import ObjectId

import pytest
from flask import url_for


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_retrieve_project_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # retrieve project
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.get(url)
        resp_data = json.loads(resp.data)

        assert resp.status == '200 OK'
        assert '_id' in resp_data
        assert 'filename' in resp_data
        assert 'storage_id' in resp_data
        assert 'create_time' in resp_data
        assert resp_data['mime_type'] == 'video/mp4'
        assert resp_data['request_address'] == '127.0.0.1'
        assert resp_data['original_filename'] == project['original_filename']
        assert resp_data['version'] == 1
        assert resp_data['parent'] is None
        assert resp_data['processing'] == {'video': False, 'thumbnail_preview': False, 'thumbnails_timeline': False}
        assert resp_data['thumbnails'] == {'timeline': [], 'preview': None}
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
def test_retrieve_project_404(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # retrieve project
        url = url_for('projects.retrieve_edit_destroy_project', project_id="definitely_not_object_id")
        resp = client.get(url)
        assert resp.status == '404 NOT FOUND'

        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        client.delete(url)
        resp = client.get(url)
        assert resp.status == '404 NOT FOUND'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_destroy_project_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.delete(url)
        assert resp.status == '204 NO CONTENT'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_destroy_project_fails(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        client.delete(url)
        resp = client.delete(url)
        assert resp.status == '404 NOT FOUND'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_edit_project_409_response(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # since we use CELERY_TASK_ALWAYS_EAGER, task will be executed immediately,
        # it means next request will return a finshed result,
        # since we want to test 409 response, we must set processing flag in db directly
        test_app.mongo.db.projects.find_one_and_update(
            {'_id': ObjectId(project['_id'])},
            {'$set': {'processing.video': True}}
        )

        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        start = 2.0
        end = 6.0
        resp = client.put(
            url,
            data=json.dumps({
                "trim": {
                    "start": start,
                    "end": end
                }
            }),
            content_type='application/json'
        )
        assert resp.status == '409 CONFLICT'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_no_edit_rules_provided(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({}),
            content_type='application/json'
        )
        assert resp.status == '400 BAD REQUEST'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_edit_project_version_1(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        start = 2.0
        end = 6.0
        resp = client.put(
            url,
            data=json.dumps({
                "trim": {
                    "start": start,
                    "end": end
                }
            }),
            content_type='application/json'
        )
        assert resp.status == '400 BAD REQUEST'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_trim_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        start = 2.0
        end = 6.0
        resp = client.put(
            url,
            data=json.dumps({
                "trim": {
                    "start": start,
                    "end": end
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert not resp_data['processing']['video']
        assert resp_data['metadata']['duration'] == end - start
        # edit request have trim end greater than duration
        old_duration = resp_data['metadata']['duration']
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        start = 2.0
        end = 20.0
        resp = client.put(
            url,
            data=json.dumps({
                "trim": {
                    "start": start,
                    "end": end
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert not resp_data['processing']['video']
        assert resp_data['metadata']['duration'] == old_duration - start


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_trim_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": {
                    "start": 6.0,
                    "end": 2.0
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': [{'start': ["must be less than 'end' value"]}]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": {
                    "start": 0,
                    "end": 1
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': [{'start': ['trimmed video must be at least 2 seconds']}]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "trim": {
                    "start": 0,
                    "end": 15
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': [{'end': ['trim is duplicating an entire video']}]}


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_rotate_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "rotate": 90
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 720
        assert resp_data['metadata']['height'] == 1280


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_edit_project_rotate_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "rotate": 70
            }),
            content_type='application/json'
        )
        assert resp.status == '400 BAD REQUEST'


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_crop_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "crop": {
                    "x": 0,
                    "y": 0,
                    "width": 640,
                    "height": 480
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 640
        assert resp_data['metadata']['height'] == 480


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_crop_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": {
                    "x": 2000,
                    "y": 0,
                    "width": 640,
                    "height": 480
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': [{'x': ['less than minimum allowed crop width']}]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": {
                    "x": 0,
                    "y": 1000,
                    "width": 640,
                    "height": 480
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': [{'y': ['less than minimum allowed crop height']}]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": {
                    "x": 300,
                    "y": 0,
                    "width": 1000,
                    "height": 480
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': [{'width': ["crop's frame is outside a video's frame"]}]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "crop": {
                    "x": 0,
                    "y": 200,
                    "width": 640,
                    "height": 600
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'crop': [{'height': ["crop's frame is outside a video's frame"]}]}


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_scale_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 640
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 640
        assert resp_data['metadata']['height'] == 360


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_scale_fail(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 0
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'scale': [f'min value is {test_app.config.get("MIN_VIDEO_WIDTH")}']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 5000
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'scale': [f'max value is {test_app.config.get("MAX_VIDEO_WIDTH")}']}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 1280
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {'trim': [{'scale': ['video or crop option already has exactly the same width']}]}

        # edit request
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 1440
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {
            'trim': [{'scale': ['interpolation is permitted only for videos which have width less than 1280px']}]
        }

        # edit request
        test_app.config['ALLOW_INTERPOLATION'] = False
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 1440
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '400 BAD REQUEST'
        assert resp_data == {
            'trim': [{'scale': ['interpolation of pixels is not allowed']}]
        }


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_scale_and_crop_success(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "scale": 640,
                "crop": {
                    "x": 0,
                    "y": 0,
                    "width": 400,
                    "height": 400
                }
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)
        assert resp_data['metadata']['width'] == 640
        assert resp_data['metadata']['height'] == 640


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': True},)], indirect=True)
def test_edit_project_remove_thumbnails(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        # capture 3 timeline thumbnails
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + '?type=timeline&amount=3'
        client.get(url)
        # capture preview thumbnail
        url = url_for(
            'projects.retrieve_or_create_thumbnails', project_id=project['_id']
        ) + '?type=preview&position=2'
        client.get(url)
        # edit request
        url = url_for('projects.retrieve_edit_destroy_project', project_id=project['_id'])
        resp = client.put(
            url,
            data=json.dumps({
                "rotate": 90
            }),
            content_type='application/json'
        )
        resp_data = json.loads(resp.data)
        assert resp.status == '202 ACCEPTED'
        assert resp_data == {'processing': True}
        # get details
        resp = client.get(url)
        resp_data = json.loads(resp.data)

        assert resp_data['thumbnails']['timeline'] == []
        # we keep preview thumbnail
        assert resp_data['thumbnails']['preview'] is not None
