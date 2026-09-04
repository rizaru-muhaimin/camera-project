from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2


@dataclass(frozen=True)
class CameraDescriptor:
    backend: str
    index: int
    name: str
    model: str = ""
    serial_number: str = ""

    @property
    def display_name(self) -> str:
        details = [self.name]
        if self.model and self.model != self.name:
            details.append(self.model)
        if self.serial_number:
            details.append(f"SN: {self.serial_number}")
        return " | ".join(details)


def list_sdk_cameras() -> list[CameraDescriptor]:
    """Return cameras discovered by the installed pytelicam SDK."""
    try:
        import pytelicam

        system = pytelicam.get_camera_system()
    except Exception:
        return []

    cameras: list[CameraDescriptor] = []
    try:
        for index in range(system.get_num_of_cameras()):
            info = system.get_camera_information(index)
            cameras.append(
                CameraDescriptor(
                    backend="pytelicam",
                    index=index,
                    name=info.cam_display_name or info.cam_vendor,
                    model=info.cam_model,
                    serial_number=info.cam_serial_number,
                )
            )
    finally:
        system.terminate()
    return cameras


def list_connected_cameras(max_index: int = 10) -> list[CameraDescriptor]:
    """Return SDK cameras and standard OpenCV cameras for the UI selector."""
    cameras = list_sdk_cameras()
    cameras.extend(
        CameraDescriptor(backend="opencv", index=index, name=name)
        for index, name in list_uvc_cameras(max_index)
    )
    return cameras


def list_camera_indices(max_index: int = 10) -> list[int]:
    """Return camera indexes available through a Windows OpenCV backend."""
    available: list[int] = []
    for index in range(max_index):
        for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
            capture = cv2.VideoCapture(index, backend)
            opened = capture.isOpened()
            capture.release()
            if opened:
                available.append(index)
                break
    return available


def list_uvc_cameras(max_index: int = 10) -> list[tuple[int, str]]:
    """Return working OpenCV indexes paired with their Windows device names."""
    try:
        from pygrabber.dshow_graph import FilterGraph

        device_names = FilterGraph().get_input_devices()
    except Exception:
        device_names = []

    if not device_names:
        return []

    probe_limit = min(max_index, len(device_names))
    cameras: list[tuple[int, str]] = []
    for index in list_camera_indices(probe_limit):
        name = device_names[index] if index < len(device_names) else f"Webcam {index}"
        cameras.append((index, name))
    return cameras


class CameraService:
    def __init__(self) -> None:
        self.capture: cv2.VideoCapture | None = None
        self.capture_backend: int | None = None
        self.last_error = ""
        self.sdk_system = None
        self.sdk_device = None
        self.sdk_stream = None
        self.sdk_image = None
        self.last_frame = None

    def open(self, camera: CameraDescriptor | int) -> bool:
        self.close()
        self.last_error = ""

        if isinstance(camera, CameraDescriptor) and camera.backend == "pytelicam":
            return self._open_sdk_camera(camera)

        index = camera.index if isinstance(camera, CameraDescriptor) else camera
        for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
            capture = cv2.VideoCapture(index, backend)
            if capture.isOpened():
                self._configure_uvc(capture)
                if not self._warm_up(capture):
                    capture.release()
                    continue
                self.capture = capture
                self.capture_backend = backend
                return True
            capture.release()
        self.last_error = f"No frame received from UVC camera index {index}"
        return False

    @staticmethod
    def _configure_uvc(capture: cv2.VideoCapture) -> None:
        """Apply conservative defaults before requesting the first UVC frame."""
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        capture.set(cv2.CAP_PROP_FPS, 30)
        capture.set(cv2.CAP_PROP_AUTO_WB, 1)
        capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)

    @staticmethod
    def _warm_up(capture: cv2.VideoCapture, attempts: int = 10) -> bool:
        for _ in range(attempts):
            success, frame = capture.read()
            if success and frame is not None and frame.size > 0:
                return True
        return False

    def _open_sdk_camera(self, camera: CameraDescriptor) -> bool:
        try:
            import pytelicam

            self.sdk_system = pytelicam.get_camera_system()
            self.sdk_device = self.sdk_system.create_device_object_from_info(
                serial_no=camera.serial_number,
                model_name=camera.model,
            )
            self.sdk_device.open()
            self.sdk_stream = self.sdk_device.cam_stream
            self.sdk_stream.open()
            self.sdk_stream.start()
            return True
        except Exception:
            self.close()
            return False

    def read(self):
        if self.sdk_stream is not None:
            try:
                image = self.sdk_stream.get_next_image(1000)
                self.sdk_image = image
                self.last_frame = image.get_ndarray().copy()
                image.release()
                self.sdk_image = None
                return self.last_frame
            except Exception:
                return None
        if self.capture is None:
            return None
        success, frame = self.capture.read()
        if not success:
            self.last_error = "Camera opened, but reading a frame failed"
            return None
        self.last_frame = frame
        return frame

    def save_frame(
        self, folder: Path, prefix: str, extension: str, quality: int
    ) -> Path:
        if self.last_frame is None:
            raise OSError("No frame is available")
        folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        path = folder / f"{prefix}_{timestamp}.{extension}"
        parameters = []
        if extension.lower() in {"jpg", "jpeg"}:
            parameters = [cv2.IMWRITE_JPEG_QUALITY, quality]
        if not cv2.imwrite(str(path), self.last_frame, parameters):
            raise OSError(f"Could not write image: {path}")
        return path

    def close(self) -> None:
        if self.sdk_image is not None:
            try:
                self.sdk_image.release()
            except Exception:
                pass
            self.sdk_image = None
        if self.sdk_stream is not None:
            try:
                self.sdk_stream.stop()
            except Exception:
                pass
            try:
                self.sdk_stream.close()
            except Exception:
                pass
            self.sdk_stream = None
        if self.sdk_device is not None:
            try:
                self.sdk_device.close()
            except Exception:
                pass
            self.sdk_device = None
        if self.sdk_system is not None:
            try:
                self.sdk_system.terminate()
            except Exception:
                pass
            self.sdk_system = None
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.capture_backend = None
        self.last_frame = None
