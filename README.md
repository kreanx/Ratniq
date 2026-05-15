# Ratniq

Desktop pet rat for Linux. A tiny pixel art rat walks across your screen and along the top edges of your open windows.

Heavily inspired by [Sill Cats](https://store.steampowered.com/app/4641700/Sill_Cats/).

## Requirements

- Linux with X11 (tested on Pop!_OS)
- Python 3.10+
- GTK3 (`python3-gi`, `gir1.2-gtk-3.0`)
- PyCairo (`python3-cairo`)
- Pillow (`pip install Pillow`)
- python-xlib (`pip install python-xlib`) — optional, improves window detection
- `wmctrl` — optional, used as fallback for window detection

## Install

```bash
pip install --break-system-packages Pillow python-xlib
```

Or use your distro packages:

```bash
sudo apt install python3-pil python3-xlib
```

## Run

```bash
python3 main.py
```

Press Ctrl+C in the terminal to quit.

## Features

- Transparent overlay — rat renders on top of all windows
- Click-through — mouse clicks pass through everywhere except on the rat
- Click the rat to pause/resume it
- Rat walks along the bottom of the screen and top edges of open windows
- Jumps between window surfaces
- State machine: idle, walking, running (zoomies 1-4 AM), sniffing (gesture), climbing
- Night zoomies mode (increased running probability between 1-4 AM)
- Window detection via wmctrl / xwininfo / python-xlib (fallback chain)

## Sprite Credits

See [ATTRIBUTION](ATTRIBUTION).

## License

Code: MIT
Sprites: CC-BY 3.0 (see ATTRIBUTION)
