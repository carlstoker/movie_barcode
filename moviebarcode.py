#!/usr/bin/env python3
import json, progressbar, subprocess, argparse
from os.path import splitext, basename, expanduser
from shutil import move
from sys import argv
from tempfile import TemporaryDirectory

def process_video():
    global settings
    # Calculate interval based on duration / number of pixels
    settings['interval'] = (settings['duration'] / settings['width'])

    with TemporaryDirectory() as settings['temp']:
        extract_frames()
        if settings['smooth']:
            resize_frames(1)
            resize_frames(settings['height'])
        combine_frames()
    return None

def extract_frames():
    global settings

    print('Extracting {width} frames from {filename} to {temp} with a {interval:.02f} second interval'.format(**settings))
    for i in progressbar.progressbar(range(settings['width'])):
        capture_time = settings['start'] + ((i + 1) * settings['interval'])

        command = [
            'ffmpeg',
            '-ss', str(capture_time),
            '-i', '{filename}'.format(**settings),
            '-vf', 'format=yuvj444p,scale=1:{height}'.format(**settings),
            '-vframes', '1',
            '-y',
            '-loglevel', 'fatal',
            '{}/frame{:05d}.jpg'.format(settings['temp'], i)]
        subprocess.call(command)

    return None

def resize_frames(height):
    global settings

    print('Resizing Frames to 1x{}'.format(height))
    command = [
        'mogrify',
        '-resize', '1x{}!'.format(height),
        '*.jpg'
    ]
    subprocess.call(command, cwd = settings['temp'])

    return None

def combine_frames():
    global settings

    print('Combining frames into montage {output}/{basename}.png'.format(**settings))
    command = [
        'montage',
        '-geometry', '+0+0',
        '-tile', 'x1',
        '*.jpg',
        'montage.png'.format(**settings)
    ]
    subprocess.call(command, cwd=settings['temp'])
    move('{temp}/montage.png'.format(**settings), '{output}/{basename}.png'.format(**settings))

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

    metadata.update({
        'duration': float(metadata['duration'])
    })
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate cinegrid for the FILEs')
    parser.add_argument('FILE', nargs='+')
    parser.add_argument('--duration', help='duration of capture (in seconds) (default: %(default)s)', default=None, metavar='DURATION'),
    parser.add_argument('--height', help='barcode height (default: %(default)s)', default=1875, metavar='PIXELS', type=int)
    parser.add_argument('--output', help='output directory (default: %(default)s)', default='~/Pictures', metavar='DIR')
    parser.add_argument('--smooth', help='enable/disable single color vertical lines (default: %(default)s)', default=True, action='store_true')
    parser.add_argument('--start', help='start point (in seconds) (default: %(default)s)', default=0, metavar='START')
    parser.add_argument('--width', help='barcode width/number of frames (default: %(default)s)', default=5000, metavar='PIXELS', type=int)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0alpha')

    settings = parser.parse_args().__dict__
    settings['output'] = expanduser(settings['output'])

    for filename in settings['FILE']:
        settings.update({'filename': filename, 'basename': splitext(basename(filename))[0]})
        metadata = get_metadata(filename)

        #Duration is capped to prevent missing frames at the end of the file
        if settings['duration'] is None:
            settings['duration'] = (metadata['duration'] * 0.95) - settings['start']
        else:
            settings['duration'] = min(settings['duration'], (metadata['duration'] * 0.95) - settings['start'])

        process_video()
