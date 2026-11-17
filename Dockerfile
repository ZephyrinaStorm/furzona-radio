FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates fonts-dejavu-core chromium xvfb x11-utils pulseaudio pulseaudio-utils && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir playwright==1.56.0
RUN useradd --create-home --uid 10001 radio
WORKDIR /app
COPY --chown=radio:radio stream.py browser_stream.py ./
COPY --chown=radio:radio assets ./assets
ENV PYTHONUNBUFFERED=1
USER radio
CMD ["python", "browser_stream.py"]
