import sys
import os

from flask import current_app as app

from lib.video_editor.ffmpeg import FFMPEGVideoEditor

editor = FFMPEGVideoEditor()


def test_ffmpeg_video_editor_cut_video(filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_cut_video.mp4', None,
        video_cut={'start': 2, 'end': 10}
    )

    assert metadata['width'] == 640
    assert metadata['height'] == 480
    assert metadata['duration'] == '8.027031'
    assert metadata['size'] == '666985'
    assert metadata['bit_rate'] == '332180'


def test_ffmpeg_video_editor_crop_video(filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_crop_video.mp4', None,
        video_crop={'width': 500, 'height': 400, 'x': 10, 'y': 10}
    )

    assert metadata['width'] == 500
    assert metadata['height'] == 400
    if sys.platform == 'linux':
        assert metadata['bit_rate'] == '553486'
        assert metadata['size'] == '2353910'


def test_ffmpeg_video_editor_rotate_video(filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_rotate_video.mp4', None,
        video_rotate={'degree': 90}
    )

    assert metadata['width'] == 480
    assert metadata['height'] == 640


def test_ffmpeg_video_editor_generate_thumbnails(client, filestream):
    metadata = editor.get_meta(filestream)
    fs_path = app.config['FS_MEDIA_STORAGE_PATH']
    filename = 'test_ffmpeg_video_editor_generate_thumbnails'
    storage_id_list = set()
    for index, (thumbnail, thumbnail_meta) in enumerate(
        editor.capture_list_timeline_thumbnails(
            filestream,
            filename,
            metadata,
            app.config.get('AMOUNT_FRAMES', 40))):
        storage_id = app.fs.put(thumbnail, f'test_generate_thumbnails/filename_{index}.png')
        storage_id_list.add(storage_id)

    assert all(os.path.exists(f'{fs_path}/{storage_id}') for storage_id in storage_id_list)


def test_ffmpeg_video_editor_capture_thumbnail(filestream):
    metadata = editor.get_meta(filestream)
    stream_meta, thumbnail_meta = editor.capture_thumbnail(
        filestream, 'test_ffmpeg_video_editor_capture_thumbnail', metadata, 10
    )

    assert thumbnail_meta['codec_name'] == 'png'
    assert thumbnail_meta['size'] == '317273'
