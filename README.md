# My Personal Radio Staton I Made — Website capture edition

This edition opens https://furzona.odoo.com/radio in a server-side Chromium browser, scrolls to its embedded player, clicks Play, and captures the actual webpage and its browser audio for YouTube. Viewers see the station's own current-song display and credits. Your Windows PC can stay off. The GIF is included but is not displayed in this edition.

## Deploy

1. Extract this ZIP. Upload the CONTENTS of personal-radio into a private GitHub repository root. Include Dockerfile, browser_stream.py, stream.py, render.yaml and assets.
2. In Render choose New → Blueprint and connect that repository. Review the paid worker's current price and bandwidth charges before creating it. The standard plan is a starting configuration; Chromium plus video encoding may require a larger plan. No domain or public HTTP port is needed.
3. Enter YOUTUBE_STREAM_KEY in Render's private Environment field. Never put it in GitHub or chat.
4. In YouTube Studio → Create → Go live, create an encoder broadcast titled: My Personal Radio Staton I Made
5. Set YOUTUBE_SERVER_URL to the server URL from YouTube Studio, preferably RTMPS. The provided default is the usual primary endpoint. Optionally set YOUTUBE_BACKUP_SERVER_URL to the exact backup server URL YouTube provides; query parameters are preserved.
6. Deploy, wait for the preview in YouTube Studio, check that the website, song information and audio appear correctly, then click Go live. Test unlisted first.
7. To stop, suspend the Render worker AND end the broadcast in YouTube Studio. Ending the YouTube broadcast alone leaves the worker running and billed.

## Update an earlier installation

Replace all repository files with this package and redeploy. Keep your existing private stream key in Render. Docker now starts browser_stream.py instead of stream.py. RADIO_URL was removed from render.yaml because website mode uses the site's own Play button.

## Behavior and limitations

- Captures a 1280×720 virtual desktop at 30fps with H.264 3Mbps video and AAC 128kbps stereo.
- Uses the actual page and its embedded Furzona player, rather than fetching the MP3 directly or drawing a separate song overlay. The website controls metadata and audio timing.
- Website, player, browser or encoder errors trigger a restart with a 10-second delay. If a backup URL is configured, attempts alternate between primary and backup; this is sequential retry, not simultaneous redundant feeds or a second server.
- Website layout changes, cookie overlays, station outages or stalled browser audio can require manual intervention. The script verifies the player switches to Stop, but that alone cannot prove audible sound; check YouTube's preview. The monitor restarts playback if the Play button returns.
- YouTube's automatic stop settings can end the broadcast during outages. Review them for continuous streaming.
- Continuous 3.128Mbps output is roughly 1 TB per 30 days before overhead. Monitor Render CPU, RAM and bandwidth usage.
- This is a radio-to-YouTube worker, with no dashboard or public website of its own.
- The live page, popups and any changes made by the station can appear in the broadcast. Use only this public station page; do not sign into personal accounts in the capture browser.
- FFmpeg error output is suppressed to avoid exposing the secret destination key.
- Displaying the website and artist credits does not prevent copyright claims. Use your permission to rebroadcast the music and website presentation. Audio remains Furzona Club Radio; it should not be presented as your own music catalog.

## Validation performed

The radio page HTML was inspected and its Furzona embed identified. The live station metadata API returned song and artist information. Python syntax and URL construction were checked; the previous image/overlay encoder produced H.264/AAC test output. This workspace blocked Chromium startup, so the website capture, browser audio and Render deployment have NOT been end-to-end tested. Verify the YouTube preview before making the stream public.
