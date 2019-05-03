from lib.video_editor.ffmpeg import FFMPEGVideoEditor
import sys

editor = FFMPEGVideoEditor()


def test_ffmpeg_video_editor_cut_video(client, filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_cut_video.mp4', None,
        video_cut={'start': 2, 'end': 10}
    )

    assert metadata['width'] == '640'
    assert metadata['height'] == '480'
    assert metadata['duration'] == '8.027031'
    assert metadata['size'] == '666985'
    assert metadata['bit_rate'] == '332180'


def test_ffmpeg_video_editor_crop_video(client, filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_crop_video.mp4', None,
        video_crop={'width': 500, 'height': 400, 'x': 10, 'y': 10}
    )

    assert metadata['width'] == '500'
    assert metadata['height'] == '400'
    if sys.platform == 'linux':
        assert metadata['bit_rate'] == '553486'
        assert metadata['size'] == '2353910'


def test_ffmpeg_video_editor_rotate_video(client, filestream):
    content, metadata = editor.edit_video(
        filestream, 'test_ffmpeg_video_editor_rotate_video.mp4', None,
        video_rotate={'degree': 90}
    )

    assert metadata['width'] == '480'
    assert metadata['height'] == '640'
