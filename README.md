# Hogwarts Wall Software

A portrait wall that loops videos in frames you can position on the screen. It has a desktop player built with Pygame and OpenCV and a browser version served by Flask.

Put your videos in `videos_sq/` or `videos_kd/` and match the filenames in the layout JSON for your chosen profile. Use `sq` or `kd` in the commands below.

For the desktop player, install FFmpeg and make sure it is on your PATH. Then run:

```sh
python -m pip install pygame-ce opencv-python
python native_app.py sq
```

Press A through Q to select a frame's audio, 0 to mute, 1 to show the debug overlay, 3 for fullscreen, or Escape to quit.

For the browser version, run:

```sh
python -m pip install -r requirements.txt
python server.py sq
```

Open [localhost:5000](http://localhost:5000). The server listens on this computer by default. Use `--host 0.0.0.0` if you need to open the display from another device on a trusted network.
