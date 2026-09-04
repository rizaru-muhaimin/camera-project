# Camera Project

Desktop camera application for Python 3.11.9, PySide6, OpenCV, and pytelicam.

## Project structure

```text
app.py                      # Application entry point
UI/camera_window.py         # PySide6 user interface
UIServices/camera_service.py # Camera discovery and capture backends
cameraSDK/                  # Local pytelicam SDK wheel only
assets/camera.svg           # Application camera icon
```

## Setup on Windows

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

The app detects cameras through both the pytelicam SDK and Windows UVC/DirectShow,
shows a realtime preview, and saves JPEG or PNG photos using the selected folder,
prefix, and quality settings. Settings are persisted with Qt `QSettings`.

## Camera usage

1. Connect the camera before starting the application.
2. Click `Refresh` to update the camera list.
3. Select one camera and click `Open camera`.
4. Click `Stop camera` before switching applications or disconnecting it.

Only the selected camera is opened. Close applications that may already use the
camera, such as Teams, OBS, or another Python camera process. A camera SDK can
report an open device while returning no frames when another process owns its
stream.

## About pytelicam

`pytelicam` is not available from the public PyPI index, but this project
contains the compatible local wheel for CPython 3.11 64-bit Windows. The wheel
is stored in `cameraSDK/` and installed into the `venv` environment by
`requirements.txt`. The SDK backend handles device open, stream start, frame
read, stream stop, and device close. Standard UVC cameras use OpenCV with
DirectShow/Media Foundation fallback.

## Application icon

The SVG icon is used by the Qt window and application. When running with
`python app.py`, Windows may still show the Python icon in the taskbar because
the process belongs to `python.exe`. A taskbar icon for distribution requires
building an executable with a Windows `.ico` resource.

Generate the Windows icon and build the executable:

```powershell
python tools\generate_icon.py
python -m PyInstaller --noconfirm --clean --windowed `
	--name CameraCapture `
	--icon=assets\camera.ico `
	--add-data "assets;assets" app.py
```

The executable is created at `dist/CameraCapture/CameraCapture.exe` and uses
the camera icon in the Windows taskbar. This build is intended for Windows
64-bit with Python 3.11 and the bundled local pytelicam wheel.