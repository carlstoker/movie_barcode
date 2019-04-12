#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from tempfile import TemporaryDirectory
import progressbar

def process_video(filename):
    global SETTINGS

    metadata = get_metadata(filename, ['duration'])

    #Prevent missing frames at the end of the file by capping duration to 95% of video duration
    if SETTINGS['duration'] == 0:
        SETTINGS['duration'] = (metadata['duration'] * 0.95) - SETTINGS['start']
    else:
        SETTINGS['duration'] = min(
            SETTINGS['duration'],
            (metadata['duration'] * 0.95) - SETTINGS['start']
        )

    SETTINGS.update({
        'filename': filename,
        'basename': os.path.splitext(os.path.basename(filename))[0],
        'frames': int(SETTINGS['width'] / SETTINGS['framewidth'])
    })
    SETTINGS.update({
        'interval': SETTINGS['duration'] / SETTINGS['frames'],
        'barcode_filename':
            '{output}/{basename}-{framewidth}x{frames}barcode.png'.format(**SETTINGS)
    })

    if not SETTINGS['overwrite'] and os.path.isfile(SETTINGS['barcode_filename']):
        print('Barcode exists. Skipping {filename}'.format(**SETTINGS))
        return False

    with TemporaryDirectory() as SETTINGS['temp']:
        extract_frames()
        combine_frames()

    return True

def extract_frames():
    global SETTINGS

    scale = []
    if not SETTINGS['rough']:
        scale.append('scale=1:1')
    scale.append('scale={framewidth}:{height}'.format(**SETTINGS))

    print('Extracting {frames} frames from {filename} to {temp} with a {interval:.02f} second interval'.format(**SETTINGS))
    for i in progressbar.progressbar(range(SETTINGS['frames'])):
        capture_time = SETTINGS['start'] + ((i + 1) * SETTINGS['interval'])

        command = [
            'ffmpeg',
            '-ss', str(capture_time),
            '-i', '{filename}'.format(**SETTINGS),
            '-vf', 'format=yuvj444p,{}'.format(','.join(scale)),
            '-vframes', '1',
            '-y',
            '-loglevel', 'fatal',
            '{}/frame{:05d}.png'.format(SETTINGS['temp'], i)]
        subprocess.call(command)

    return None

def combine_frames():
    global SETTINGS

    print('Combining frames into montage {output}/{basename}.png'.format(**SETTINGS))
    command = [
        'montage',
        '-geometry', '+0+0',
        '-tile', 'x1',
        'frame*.png',
        'montage.png'.format(**SETTINGS)
    ]
    subprocess.call(command, cwd=SETTINGS['temp'])
    shutil.move('{temp}/montage.png'.format(**SETTINGS), '{barcode_filename}'.format(**SETTINGS))

    return None

def get_metadata(fname, keys):
    """Return metadata for filename

    Arguments:
    fname -- filename to retrieve metadata from
    keys -- keys to look for and save
    """
    command = [
        'ffprobe',
        '-show_entries', 'stream={0}:format={0}'.format(','.join(keys)),
        '-of', 'json',
        '-v', 'error',
        fname
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
    PARSER = argparse.ArgumentParser(description='Generate barcode for the FILE(s)')
    PARSER.add_argument('FILE', nargs='+')
    PARSER.add_argument('--duration', help='duration of capture (in seconds)',
                        default=0, metavar='DURATION', type=float)
    PARSER.add_argument('--framewidth', help='width for each frame (default: %(default)s)',
                        default=1, metavar='PIXELS', type=int)
    PARSER.add_argument('--height', help='height of barcode (default: %(default)s)',
                        default=1875, metavar='PIXELS', type=int)
    PARSER.add_argument('--interactive',
                        help='prompt for each file\'s new title (default: %(default)s)',
                        default=False, action='store_true')
    PARSER.add_argument('--output', help='output directory (default: %(default)s)',
                        default='~/Pictures', metavar='DIR')
    PARSER.add_argument('--overwrite', help='overwrite existing cinegrid (default: %(default)s)',
                        default=False, action='store_true')
    PARSER.add_argument('--prompt',
                        help='prompt before exiting (default: %(default)s)',
                        default=False, action='store_true')
    PARSER.add_argument('--rough', help='disable single color vertical lines (default: %(default)s)',
                        default=False, action='store_true')
    PARSER.add_argument('--start', help='start point (in seconds) (default: %(default)s)',
                        default=0, metavar='START', type=float)
    PARSER.add_argument('--width', help='width of barcode (default: %(default)s)',
                        default=5000, metavar='PIXELS', type=int)
    PARSER.add_argument('--version', action='version', version='%(prog)s 1.0alpha')

    SETTINGS = PARSER.parse_args().__dict__
    SETTINGS['output'] = os.path.expanduser(SETTINGS['output'])
    if SETTINGS['interactive']:
        SETTINGS.update({
            'start': float(input('Enter start time (in seconds) [0]: ') or 0),
            'duration': float(input('Enter duration (in seconds) [0]: ') or 0),
            'height': int(input('Enter height (in pixels) [1875]: ') or 1875),
            'width': int(input('Enter width (in pixels) [5000]: ') or 5000),
            'framewidth': int(input('Enter frame width (in pixels) [1]: ') or 1)
        })

    for filename in SETTINGS['FILE']:
        process_video(filename)
    if SETTINGS['prompt']:
        input('Press Enter to continue.')
