#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
from tempfile import TemporaryDirectory
import progressbar

def process_video(filename):
    global settings

    metadata = get_metadata(filename)

    #Prevent missing frames at the end of the file by capping duration to 95% of video duration
    if settings['duration'] == 0:
        settings['duration'] = (metadata['duration'] * 0.95) - settings['start']
    else:
        settings['duration'] = min(
            settings['duration'],
            (metadata['duration'] * 0.95) - settings['start']
        )

    settings.update({
        'filename': filename,
        'basename': os.path.splitext(os.path.basename(filename))[0],
        'frames': int(settings['width'] / settings['framewidth'])
    })
    settings.update({
        'interval': settings['duration'] / settings['frames'],
        'barcode_filename':
            '{output}/{basename}-{framewidth}x{frames}barcode.png'.format(**settings)
    })

    if not settings['overwrite'] and os.path.isfile(settings['barcode_filename']):
        print('Barcode exists. Skipping {filename}'.format(**settings))
        return False

    with TemporaryDirectory() as settings['temp']:
        extract_frames()
        combine_frames()

    return True

def extract_frames():
    global settings

    scale = []
    if not settings['rough']:
        scale.append('scale=1:1')
    scale.append('scale={framewidth}:{height}'.format(**settings))

    print('Extracting {frames} frames from {filename} to {temp} with a {interval:.02f} second interval'.format(**settings))
    for i in progressbar.progressbar(range(settings['frames'])):
        capture_time = settings['start'] + ((i + 1) * settings['interval'])

        command = [
            'ffmpeg',
            '-ss', str(capture_time),
            '-i', '{filename}'.format(**settings),
            '-vf', 'format=yuvj444p,{}'.format(','.join(scale)),
            '-vframes', '1',
            '-y',
            '-loglevel', 'fatal',
            '{}/frame{:05d}.png'.format(settings['temp'], i)]
        subprocess.call(command)

    return None

def combine_frames():
    global settings

    print('Combining frames into montage {output}/{basename}.png'.format(**settings))
    command = [
        'montage',
        '-geometry', '+0+0',
        '-tile', 'x1',
        'frame*.png',
        'montage.png'.format(**settings)
    ]
    subprocess.call(command, cwd=settings['temp'])
    shutil.move('{temp}/montage.png'.format(**settings), '{barcode_filename}'.format(**settings))

    return None

def get_metadata(filename):
    command = [
        'ffprobe',
        '-show_entries', 'stream=duration:format=duration',
        '-of', 'json',
        '-v', 'error',
        filename
    ]
    j = json.loads(subprocess.check_output(command))

    metadata = {}
    for key in ['duration']:
        for dict in j['streams']:
            if key in dict:
                metadata[key] = dict[key]
                break

    if 'duration' not in metadata:
        metadata['duration'] = j['format']['duration']

    metadata['duration'] = float(metadata['duration'])
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate barcode for the FILE(s)')
    parser.add_argument('FILE', nargs='+')
    parser.add_argument('--duration', help='duration of capture (in seconds)',
                        default=0, metavar='DURATION', type=float)
    parser.add_argument('--framewidth', help='width for each frame (default: %(default)s)',
                        default=1, metavar='PIXELS', type=int)
    parser.add_argument('--height', help='height of barcode (default: %(default)s)',
                        default=1875, metavar='PIXELS', type=int)
    parser.add_argument('--interactive',
                        help='prompt for each file\'s new title (default: %(default)s)',
                        default=False, action='store_true')
    parser.add_argument('--output', help='output directory (default: %(default)s)',
                        default='~/Pictures', metavar='DIR')
    parser.add_argument('--overwrite', help='overwrite existing cinegrid (default: %(default)s)',
                        default=False, action='store_true')
    parser.add_argument('--prompt',
                        help='prompt before exiting (default: %(default)s)',
                        default=False, action='store_true')
    parser.add_argument('--rough', help='disable single color vertical lines (default: %(default)s)',
                        default=False, action='store_true')
    parser.add_argument('--start', help='start point (in seconds) (default: %(default)s)',
                        default=0, metavar='START', type=float)
    parser.add_argument('--width', help='width of barcode (default: %(default)s)',
                        default=5000, metavar='PIXELS', type=int)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0alpha')

    settings = parser.parse_args().__dict__
    settings['output'] = os.path.expanduser(settings['output'])
    if settings['interactive']:
        settings.update({
            'start': float(input('Enter start time (in seconds) [0]: ') or 0),
            'duration': float(input('Enter duration (in seconds) [0]: ') or 0),
            'height': int(input('Enter height (in pixels) [1875]: ') or 1875),
            'width': int(input('Enter width (in pixels) [5000]: ') or 5000),
            'framewidth': int(input('Enter frame width (in pixels) [1]: ') or 1)
        })

    for filename in settings['FILE']:
        process_video(filename)
    if settings['prompt']:
        input('Press Enter to continue.')
