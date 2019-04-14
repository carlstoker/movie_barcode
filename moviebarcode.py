#!/usr/bin/env python3
"""Generate barcode for video input(s)."""

import argparse
import json
import os
import shutil
import subprocess
from tempfile import TemporaryDirectory
import progressbar


def generate_barcode(filename, output_directory, start_time, duration, height, width, frame_directory, framewidth, overwrite=False, rough=False):
    """Generate barcode from specified filename.

    Arguments:
    filename -- filename to use for barcode generation
    output_directory -- output directory for barcode
    start_time -- start time to start grabbing frames
    duration -- duration to grab frames
    height -- height of final barcode
    width -- width of final barcode
    frame_directory -- directory to store frames
    framewidth -- width of each bar
    overwrite -- overwrite previously generated barcode (default: False)
    rough -- disable single color vertical lines (default: False)
    """
    metadata = get_metadata(filename, ['duration'])

    # Caps capture duration to 95% of video duration
    # to prevent missing frames at the end of the file.
    if duration == 0:
        duration = (metadata['duration'] * 0.95) - start_time
    else:
        duration = min(
            duration,
            (metadata['duration'] * 0.95) - start_time
        )

    basename = os.path.splitext(os.path.basename(filename))[0]
    frames = int(width / framewidth)
    interval = duration / frames
    barcode_filename = os.path.join(
        output_directory,
        '{0}-{1}x{2}x{3}.png'.format(basename, framewidth, height, frames)
    )

    if not overwrite and os.path.isfile(barcode_filename):
        print('Barcode exists. Skipping {0}'.format(filename))
        return False

    extract_frames(
        filename,
        frame_directory,
        start_time,
        interval,
        frames,
        height,
        framewidth,
        rough
    )
    combine_frames(frame_directory, barcode_filename)

    return True


def extract_frames(filename, frame_directory, start_time, interval, frames, height, width, rough=False):
    """Extract individual frames for processing.

    Arguments:
    filename -- file from which to extract frames
    frame_directory -- directory to store frames
    start_time -- start time for capturing frames
    interval -- interval between frames
    frames -- number of frames to capture
    width -- width of each frame to capture
    height -- height of each frame to capture
    rough -- disable unicolor vertical lines (default: False)
    """

    scale = []
    if not rough:
        scale.append('scale=1:1')
    scale.append('scale={0}:{1}'.format(width, height))

    print('Extracting {0} frames from {1} to {2} with a {3:.02f} second interval'.format(
        frames, filename, frame_directory, interval))
    for i in progressbar.progressbar(range(frames)):
        capture_time = start_time + ((i + 1) * interval)

        command = [
            'ffmpeg',
            '-ss', str(capture_time),
            '-i', filename,
            '-vf', 'format=yuvj444p,{0}'.format(','.join(scale)),
            '-vframes', '1',
            '-y',
            '-loglevel', 'fatal',
            os.path.join(frame_directory, 'frame{0:05d}.png'.format(i))
        ]
        subprocess.call(command)

    return None


def combine_frames(input_directory, output_filename):
    """Combine individual frames into a montage.

    Arguments:
    input_directory -- input_directory with individual frames
    output_filename -- filename for output file
    """

    print('Combining frames into montage {0}'.format(output_filename))

    command = [
        'montage',
        '-geometry', '+0+0',
        '-tile', 'x1',
        'frame*.png',
        'montage.png'
    ]
    subprocess.call(command, cwd=input_directory)

    shutil.move(os.path.join(input_directory, 'montage.png'), output_filename)

    return None


def get_metadata(filename, keys):
    """Return metadata for filename

    Arguments:
    filename -- filename to retrieve metadata from
    keys -- keys to look for and save
    """
    command = [
        'ffprobe',
        '-show_entries', 'stream={0}:format={0}'.format(','.join(keys)),
        '-of', 'json',
        '-v', 'error',
        filename
    ]
    j = json.loads(subprocess.check_output(command))

    metadata = {}
    for key in keys:
        for stream in j['streams']:
            if key in stream:
                metadata[key] = stream[key]
                break
        if key not in metadata and key in j['format']:
            metadata[key] = j['format'][key]

    if 'duration' in metadata:
        metadata['duration'] = float(metadata['duration'])

    return metadata


if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        description='Generate barcode for the FILE(s)'
    )
    PARSER.add_argument(
        'FILE',
        nargs='+'
    )
    PARSER.add_argument(
        '--duration',
        help='duration of capture (in seconds)',
        default=0,
        metavar='DURATION',
        type=float
    )
    PARSER.add_argument(
        '--framewidth',
        help='width for each frame (default: %(default)s)',
        default=1,
        metavar='PIXELS',
        type=int
    )
    PARSER.add_argument(
        '--height',
        help='height of barcode (default: %(default)s)',
        default=1875,
        metavar='PIXELS',
        type=int)
    PARSER.add_argument(
        '--interactive',
        help='prompt for each file\'s new title (default: %(default)s)',
        default=False,
        action='store_true'
    )
    PARSER.add_argument(
        '--output',
        help='output directory (default: %(default)s)',
        default='~/Pictures',
        metavar='DIR'
    )
    PARSER.add_argument(
        '--overwrite',
        help='overwrite existing cinegrid (default: %(default)s)',
        default=False,
        action='store_true'
    )
    PARSER.add_argument(
        '--prompt',
        help='prompt before exiting (default: %(default)s)',
        default=False,
        action='store_true'
    )
    PARSER.add_argument(
        '--rough',
        help='disable single color vertical lines (default: %(default)s)',
        default=False,
        action='store_true'
    )
    PARSER.add_argument(
        '--start',
        help='start point (in seconds) (default: %(default)s)',
        default=0,
        metavar='START',
        type=float
    )
    PARSER.add_argument(
        '--width',
        help='width of barcode (default: %(default)s)',
        default=5000,
        metavar='PIXELS',
        type=int
    )
    PARSER.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0alpha'
    )

    SETTINGS = PARSER.parse_args().__dict__
    SETTINGS['output'] = os.path.expanduser(SETTINGS['output'])
    if SETTINGS['interactive']:
        SETTINGS.update({
            'start': float(input('Enter start time (seconds) [0]: ') or 0),
            'duration': float(input('Enter duration (seconds) [0]: ') or 0),
            'height': int(input('Enter height (pixels) [1875]: ') or 1875),
            'width': int(input('Enter width (pixels) [5000]: ') or 5000),
            'framewidth': int(input('Enter frame width (pixels) [1]: ') or 1)
        })

    for file in SETTINGS['FILE']:
        with TemporaryDirectory() as temp:
            generate_barcode(
                file,
                SETTINGS['output'],
                SETTINGS['start'],
                SETTINGS['duration'],
                SETTINGS['height'],
                SETTINGS['width'],
                temp,
                SETTINGS['framewidth'],
                SETTINGS['overwrite'],
                SETTINGS['rough']
            )
    if SETTINGS['prompt']:
        input('Press Enter to continue.')
