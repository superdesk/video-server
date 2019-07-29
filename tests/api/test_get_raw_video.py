from bson import ObjectId

import pytest
from flask import url_for


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_get_raw_video_full(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.get_raw_video', project_id=project['_id'])
        resp = client.get(url)

        assert resp.status == '200 OK'
        assert resp.mimetype == 'video/mp4'
        assert resp.is_streamed
        assert resp.content_length > 2600000  # just to avoid OS specific tiny file size differences


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_get_raw_video_range(test_app, client, projects):
    project = projects[0]

    with test_app.test_request_context():
        url = url_for('projects.get_raw_video', project_id=project['_id'])
        resp = client.get(
            url,
            headers={"Range": "bytes=200-"}
        )

        assert resp.status == '206 PARTIAL CONTENT'
        assert resp.mimetype == 'video/mp4'
        assert resp.is_streamed
        # TODO check resp.content_length


@pytest.mark.parametrize('projects', [({'file': 'sample_0.mp4', 'duplicate': False},)], indirect=True)
def test_get_raw_video_409_resp(test_app, client, projects):
    project = projects[0]

    # since we use CELERY_TASK_ALWAYS_EAGER, task will be executed immediately,
    # it means next request will return a finshed result,
    # since we want to test 409 response, we must set processing flag in db directly
    test_app.mongo.db.projects.find_one_and_update(
        {'_id': ObjectId(project['_id'])},
        {'$set': {'processing.video': True}}
    )

    with test_app.test_request_context():
        url = url_for('projects.get_raw_video', project_id=project['_id'])
        resp = client.get(url)

        assert resp.status == '409 CONFLICT'
