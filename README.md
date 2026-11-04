# Hogwarts Wall Software

A moving portrait wall that plays multiple looping videos in independently positioned frames. Includes a native Pygame/OpenCV player with threaded video decoding and a browser display served by Flask.

## Native player

Run from this directory with desktop Python:

```powershell
python -m pip install pygame-ce opencv-python
python native_app.py sq
```

Choose `sq` or `kd` to load the corresponding layout and `videos_sq/` or `videos_kd/` directory. Supply your own videos matching the filenames in the configuration JSON files. FFmpeg must be on PATH to extract audio.

Controls: A–Q selects a frame's audio, 0 mutes all audio, 1 toggles the debug overlay, 3 toggles fullscreen, and Escape exits.

## Browser display

```powershell
python -m pip install -r requirements.txt
python server.py sq
```

Open http://localhost:5000. The server binds to all network interfaces and runs Flask's development server; use it on a trusted local network.

## Other tools

- `downscale_videos.py`, `optimize_videos.py`, and `normalize_audio.py`: media preparation utilities; inspect their input and output settings before running.
- `native_control.py`: an earlier layout control panel using the unprofiled names `config.json` and `native_config.json`.

Personal video assets, original media, and generated audio caches are excluded from Git. Existing layout configurations are included. Playback performance and HD capacity depend on the computer and source videos.
