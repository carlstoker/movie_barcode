#!/usr/bin/env python3
import json, progressbar, subprocess
from os.path import splitext, basename, expanduser
from shutil import move
from sys import argv
from tempfile import TemporaryDirectory

settings = {
    'width': 5000,
    'height': 1875,
    'directory': '~/Pictures',
    'smooth': True
}
settings['directory'] = expanduser(settings['directory'])

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

    print('Extracting {width} frames to {temp} with a {interval:.02f} second interval'.format(**settings))
    for i in progressbar.progressbar(range(settings['width'])):
        capture_time = settings['start'] + ((i + 1) * settings['interval'])

        command = [
            'ffmpeg',
            '-ss', str(capture_time),
            '-i', '{filename}'.format(**settings),
            '-vf', 'scale=1:{height}'.format(**settings),
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

    print('Combining frames into montage {directory}/{basename}.png'.format(**settings))
    command = [
        'montage',
        '-geometry', '+0+0',
        '-tile', 'x1',
        '*.jpg',
        'montage.png'.format(**settings)
    ]
    subprocess.call(command, cwd=settings['temp'])
    move('{temp}/montage.png'.format(**settings), '{directory}/{basename}.png'.format(**settings))

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
    print('Creating barcodes for:\n{}'.format('\n'.join(argv[1:])))

    for filename in argv[1:]:
        settings.update({'filename': filename, 'basename': splitext(basename(filename))[0]})
        metadata = get_metadata(filename)
        print('Creating barcode for {}'.format(settings['filename']))

        try:
            settings['start'] = int(input("Enter timecode (in seconds) of the start of the video: "))
        except:
            settings['start'] = 0

        try:
            settings['duration'] = float(input("Enter duration (in seconds) of the video to capture: "))
        except:
            settings['duration'] = metadata['duration']

        #Duration is capped to prevent missing frames at the end of the file
        settings['duration'] = min(settings['duration'], (metadata['duration'] * 0.95) - settings['start'])

        process_video()
