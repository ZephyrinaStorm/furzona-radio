"""Capture the actual radio website and its browser audio for YouTube."""
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
from stream import destination

stop = threading.Event()
children = []

def shutdown(*_):
    stop.set()

def launch(args, **kwargs):
    proc = subprocess.Popen(args, **kwargs)
    children.append(proc)
    return proc

def wait_for(args):
    for _ in range(30):
        if subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            return
        if stop.wait(1):
            raise RuntimeError('Stopping')
    raise RuntimeError('Display/audio startup failed')

def start_player(page):
    page.goto('https://furzona.odoo.com/radio', wait_until='domcontentloaded', timeout=60000)
    player = page.locator('iframe[src*="furzona.radio/public/clubradio/embed"]').first
    player.wait_for(state='attached', timeout=30000)
    # At desktop size the page can contain both mobile and desktop copies.
    for element in page.locator('iframe[src*="furzona.radio/public/clubradio/embed"]').all():
        if element.is_visible():
            player = element
            break
    player.scroll_into_view_if_needed()
    page.evaluate('(el) => { const y=el.getBoundingClientRect().top+window.scrollY-250; window.scrollTo(0,Math.max(0,y)); }', player.element_handle())
    frame = player.element_handle().content_frame()
    frame.get_by_role('button', name='Play', exact=True).first.click(timeout=45000)
    frame.get_by_role('button', name='Stop', exact=True).first.wait_for(timeout=30000)
    print('Radio website player started; capturing website and browser audio.', flush=True)
    return frame

def encoder(target):
    return ['ffmpeg', '-hide_banner', '-nostdin', '-loglevel', 'error',
            '-thread_queue_size', '512', '-f', 'x11grab', '-framerate', '30',
            '-video_size', '1280x720', '-i', ':99.0',
            '-thread_queue_size', '512', '-f', 'pulse', '-i', 'radio.monitor',
            '-c:v', 'libx264', '-preset', 'veryfast', '-threads', '2', '-pix_fmt', 'yuv420p',
            '-b:v', '3000k', '-minrate', '3000k', '-maxrate', '3000k', '-bufsize', '6000k',
            '-x264-params', 'nal-hrd=cbr:force-cfr=1', '-g', '60', '-sc_threshold', '0',
            '-c:a', 'aac', '-b:a', '128k', '-ar', '44100', '-ac', '2',
            '-af', 'aresample=async=1', '-rw_timeout', '15000000', '-f', 'flv', target]

def main():
    key = os.getenv('YOUTUBE_STREAM_KEY', '').strip()
    if not key:
        raise SystemExit('Set YOUTUBE_STREAM_KEY privately in Render Environment.')
    servers = [os.getenv('YOUTUBE_SERVER_URL', 'rtmps://a.rtmps.youtube.com/live2')]
    if os.getenv('YOUTUBE_BACKUP_SERVER_URL', '').strip():
        servers.append(os.environ['YOUTUBE_BACKUP_SERVER_URL'].strip())
    targets = [destination(s, key) for s in servers]
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    os.environ['DISPLAY'] = ':99'
    os.environ['PULSE_SINK'] = 'radio'
    try:
        launch(['Xvfb', ':99', '-screen', '0', '1280x720x24', '-ac', '-nolisten', 'tcp'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for(['xdpyinfo', '-display', ':99'])
        launch(['pulseaudio', '--daemonize=no', '--exit-idle-time=-1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_for(['pactl', 'info'])
        subprocess.run(['pactl', 'load-module', 'module-null-sink', 'sink_name=radio', 'sink_properties=device.description=Radio'], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['pactl', 'set-default-sink', 'radio'], check=True)
        attempt = 0
        while not stop.is_set():
            broadcast = None
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=False,
                        ignore_default_args=['--mute-audio'], args=[
                            '--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu',
                            '--autoplay-policy=no-user-gesture-required', '--kiosk',
                            '--window-position=0,0', '--window-size=1280,720', '--hide-scrollbars'])
                    context = browser.new_context(viewport={'width':1280, 'height':720}, locale='en-US')
                    page = context.new_page()
                    frame = start_player(page)
                    broadcast = launch(encoder(targets[attempt % len(targets)]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    last_check = time.monotonic()
                    while not stop.wait(1):
                        if broadcast.poll() is not None:
                            raise RuntimeError('Encoder stopped')
                        if time.monotonic() - last_check > 30:
                            # A stopped player is restarted through the same website button.
                            play = frame.get_by_role('button', name='Play', exact=True)
                            if play.count() and play.first.is_visible():
                                play.first.click(timeout=10000)
                            last_check = time.monotonic()
                    browser.close()
            except Exception:
                # Do not log encoder arguments or exceptions containing the secret URL.
                print('Website/player/encoder interrupted; restarting in 10 seconds. Check station availability and YouTube settings.', flush=True)
            finally:
                if broadcast and broadcast.poll() is None:
                    broadcast.terminate()
                    try:
                        broadcast.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        broadcast.kill()
                        broadcast.wait()
            attempt += 1
            stop.wait(10)
    finally:
        for proc in reversed(children):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

if __name__ == '__main__':
    main()
