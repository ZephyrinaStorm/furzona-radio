import os
import signal
import subprocess
import threading
import json
import textwrap
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path

ROOT = Path(__file__).resolve().parent
stop = threading.Event()
child = None
SONG_FILE = Path('/tmp/radio-now-playing.txt')

def write_song(text):
    temporary = SONG_FILE.with_suffix('.tmp')
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(SONG_FILE)

def metadata_loop():
    while not stop.is_set():
        try:
            req = urllib.request.Request(
                'https://furzona.radio/api/nowplaying/clubradio',
                headers={'User-Agent': 'PersonalRadio/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.load(response)
            song = data.get('now_playing', {}).get('song', {})
            title = ' '.join(str(song.get('title') or 'Unknown title').split())
            artist = ' '.join(str(song.get('artist') or 'Unknown artist').split())
            write_song('Furzona Club Radio | Now playing\n' +
                       textwrap.fill(title[:150], width=65) + '\n' +
                       textwrap.fill(artist[:150], width=65))
        except Exception:
            write_song('Furzona Club Radio\nSong information temporarily unavailable')
        stop.wait(10)


def destination(server, key):
    p = urlsplit(server)
    if p.scheme not in ('rtmp', 'rtmps') or not p.netloc:
        raise ValueError('YouTube server must be an RTMP or RTMPS URL')
    return urlunsplit((p.scheme, p.netloc, p.path.rstrip('/') + '/' + key, p.query, p.fragment))

def command(output, audio=None, duration=None):
    args = ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'warning',
            '-re', '-stream_loop', '-1', '-i', str(ROOT / 'assets/background.gif')]
    if audio:
        args += ['-f', 'lavfi', '-i', audio]
    else:
        args += ['-rw_timeout', '15000000', '-reconnect', '1', '-reconnect_streamed', '1',
                 '-reconnect_at_eof', '1', '-reconnect_delay_max', '5', '-i',
                 os.getenv('RADIO_URL', 'https://furzona.radio/listen/clubradio/stream.mp3')]
    args += ['-map', '0:v:0', '-map', '1:a:0', '-vf',
             'fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,drawbox=x=0:y=540:w=iw:h=180:color=black@0.85:t=fill,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile=/tmp/radio-now-playing.txt:reload=1:expansion=none:fontcolor=white:fontsize=24:x=30:y=560:line_spacing=6',
             '-c:v', 'libx264', '-preset', 'veryfast', '-threads', '2', '-pix_fmt', 'yuv420p',
             '-b:v', '3000k', '-minrate', '3000k', '-maxrate', '3000k', '-bufsize', '6000k',
             '-x264-params', 'nal-hrd=cbr:force-cfr=1', '-g', '60', '-keyint_min', '60', '-sc_threshold', '0',
             '-c:a', 'aac', '-b:a', '128k', '-ar', '44100', '-ac', '2', '-af', 'aresample=async=1']
    if duration:
        args += ['-t', str(duration)]
    return args + ['-rw_timeout', '15000000', '-f', 'flv', output]

def shutdown(*_):
    stop.set()
    if child and child.poll() is None:
        child.terminate()

def main():
    global child
    key = os.getenv('YOUTUBE_STREAM_KEY', '').strip()
    if not key or key == 'REPLACE_ME':
        raise SystemExit('Set YOUTUBE_STREAM_KEY privately in Render Environment before starting.')
    servers = [os.getenv('YOUTUBE_SERVER_URL', 'rtmps://a.rtmps.youtube.com/live2')]
    backup = os.getenv('YOUTUBE_BACKUP_SERVER_URL', '').strip()
    if backup:
        servers.append(backup)
    outputs = [destination(s, key) for s in servers]
    write_song('Furzona Club Radio\nLoading current song...')
    threading.Thread(target=metadata_loop, daemon=True).start()
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    attempt = 0
    while not stop.is_set():
        print('Starting radio encoder; destination ' + str(attempt % len(outputs) + 1), flush=True)
        # Suppress FFmpeg stderr: connection errors can contain the secret output URL.
        child = subprocess.Popen(command(outputs[attempt % len(outputs)]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            while child.poll() is None and not stop.wait(1):
                pass
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
        if not stop.is_set():
            print('Encoder stopped. Check station availability and YouTube settings. Retrying in 10 seconds.', flush=True)
            attempt += 1
            stop.wait(10)

if __name__ == '__main__':
    main()
