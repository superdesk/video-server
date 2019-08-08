import pytest

from videoserver.lib.video_editor.ffmpeg import FFMPEGVideoEditor


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_ffmpeg_video_editor_trim(test_app, filestreams):
    editor = FFMPEGVideoEditor()
    mp4_stream = filestreams[0]

    with test_app.app_context():
        content, metadata = editor.edit_video(
            stream_file=mp4_stream,
            filename='test_ffmpeg_video_editor_sample.mp4',
            trim={'start': 2, 'end': 10}
        )
        assert metadata['duration'] == 8.0
        content, metadata = editor.edit_video(
            stream_file=mp4_stream,
            filename='test_ffmpeg_video_editor_sample.mp4',
            trim={'start': 0, 'end': 3}
        )
        assert metadata['duration'] == 3.0


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_ffmpeg_video_editor_crop(test_app, filestreams):
    editor = FFMPEGVideoEditor()
    mp4_stream = filestreams[0]

    with test_app.app_context():
        content, metadata = editor.edit_video(
            stream_file=mp4_stream,
            filename='test_ffmpeg_video_editor_sample.mp4',
            crop={
                'x': 0,
                'y': 0,
                'width': 640,
                'height': 480
            }
        )
        assert metadata['width'] == 640
        assert metadata['height'] == 480


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_ffmpeg_video_editor_rotate(test_app, filestreams):
    editor = FFMPEGVideoEditor()
    mp4_stream = filestreams[0]

    with test_app.app_context():
        content, metadata = editor.edit_video(
            stream_file=mp4_stream,
            filename='test_ffmpeg_video_editor_sample.mp4',
            rotate=90
        )
        assert metadata['width'] == 720
        assert metadata['height'] == 1280


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_ffmpeg_video_editor_scale(test_app, filestreams):
    editor = FFMPEGVideoEditor()
    mp4_stream = filestreams[0]

    with test_app.app_context():
        content, metadata = editor.edit_video(
            stream_file=mp4_stream,
            filename='test_ffmpeg_video_editor_sample.mp4',
            scale=640
        )
        assert metadata['width'] == 640
        # keep ratio
        assert metadata['height'] == 720 / 2


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_ffmpeg_video_editor_all_methods(test_app, filestreams):
    editor = FFMPEGVideoEditor()
    mp4_stream = filestreams[0]

    with test_app.app_context():
        content, metadata = editor.edit_video(
            stream_file=mp4_stream,
            filename='test_ffmpeg_video_editor_sample.mp4',
            trim={'start': 0, 'end': 3},
            crop={
                'x': 0,
                'y': 0,
                'width': 640,
                'height': 480
            },
            scale=320,
            rotate=90

        )
        assert metadata['duration'] == 3.0
        assert metadata['width'] == 240
        assert metadata['height'] == 320


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_ffmpeg_video_editor_capture_timeline_thumbnails(test_app, filestreams):
    editor = FFMPEGVideoEditor()
    mp4_stream = filestreams[0]

    with test_app.app_context():
        filename = 'test_ffmpeg_video_editor_sample.mp4'
        thumbnails_generator = editor.capture_timeline_thumbnails(mp4_stream, filename, 15, 10)

        for i, (thumbnail, meta) in enumerate(thumbnails_generator):
            assert thumbnail.__class__ is bytes
            assert meta['codec_name'] == 'png'
            assert meta['mimetype'] == 'image/png'
            assert meta['width'] == 89
            assert meta['height'] == 50


@pytest.mark.parametrize('filestreams', [('sample_0.mp4',)], indirect=True)
def test_ffmpeg_video_editor_capture_thumbnail(test_app, filestreams):
    editor = FFMPEGVideoEditor()
    mp4_stream = filestreams[0]

    with test_app.app_context():
        filename = 'test_ffmpeg_video_editor_sample.mp4'
        thumbnail, meta = editor.capture_thumbnail(
            stream_file=mp4_stream,
            filename=filename,
            duration=15,
            position=5,
            crop={'width': 720, 'height': 360, 'x': 0, 'y': 0},
            rotate=90
        )

        assert thumbnail.__class__ is bytes
        assert meta['codec_name'] == 'png'
        assert meta['mimetype'] == 'image/png'
        assert meta['width'] == 360
        assert meta['height'] == 720
