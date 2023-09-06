import sys
import typing

from PyQt5 import QtCore, QtMultimedia, QtGui
from PyQt5.Qt import Qt, QImage, QPainter, QBrush, QRect, QWindow, QPixmap
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget

import config
from services.singleton import SingletonMeta
import ui.settings_control_panel as settings_control_panel_ui


def mask_image(image, size=64):
    # Load image
    # image = QImage.fromData(imgdata, imgtype)

    # convert image to 32-bit ARGB (adds an alpha
    # channel ie transparency factor):
    image.convertToFormat(QImage.Format_ARGB32)

    # Crop image to a square:
    imgsize = min(image.width(), image.height())
    rect = QRect(
        (image.width() - imgsize) // 2,
        (image.height() - imgsize) // 2,
        imgsize,
        imgsize,
    )

    image = image.copy(rect)

    # Create the output image with the same dimensions
    # and an alpha channel and make it completely transparent:
    out_img = QImage(imgsize, imgsize, QImage.Format_ARGB32)
    out_img.fill(Qt.transparent)

    # Create a texture brush and paint a circle
    # with the original image onto the output image:
    brush = QBrush(image)

    # Paint the output image
    painter = QPainter(out_img)
    painter.setBrush(brush)

    # Don't draw an outline
    painter.setPen(Qt.NoPen)

    # drawing circle
    painter.drawEllipse(0, 0, imgsize, imgsize)

    # closing painter event
    painter.end()

    # Convert the image to a pixmap and rescale it.
    pr = QWindow().devicePixelRatio()
    pm = QPixmap.fromImage(out_img)
    pm.setDevicePixelRatio(pr)
    size = int(size * pr)
    pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # return back the pixmap data
    return pm


class SettingsPanelWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = settings_control_panel_ui.Ui_Form()
        self.ui.setupUi(self)


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_panel = SettingsPanelWidget(self)
        self.layout = QVBoxLayout(self)
        self.camera = LabelCamera(camera_id=0, size=None, parent=self)
        self.layout.addWidget(self.camera)
        self.layout.addWidget(self.settings_panel)
        self.settings_panel.ui.cameras_list.currentIndexChanged.connect(
            self.change_camera
        )
        self.available_cameras = []

        self.camera.start_camera()

    def change_camera(self, item_id):
        camera_name = self.settings_panel.ui.cameras_list.currentText()
        print(item_id, camera_name)
        self.camera.change_camera_id(item_id)
        # print(self.available_cameras, camera_name)
        # try:
        #     camera_id = self.available_cameras.index(camera_name)
        # except:
        #     ...

    def update_cameras_list(self):
        self.available_cameras = self.camera.get_available_cameras()
        cameras_names = list(map(lambda x: x.description(), self.available_cameras))
        self.settings_panel.ui.cameras_list.addItems(cameras_names)

    def showEvent(self, a0) -> None:
        self.update_cameras_list()
        return super().showEvent(a0)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)
        menu = QMenu()
        self.settingsAction = menu.addAction("Settings")
        self.showOrHideAction = menu.addAction("Show/Hide")
        self.exitAction = menu.addAction("Exit")
        self.setContextMenu(menu)


class Camera(metaclass=SingletonMeta):
    def __init__(self, camera_id=0):
        self.sources = {}

        self.viewfinder = QCameraViewfinder()
        self.probe = None

        self.change_camera_id(camera_id)

    def get_size_or_camera_size(self):
        size = self.viewfinder.size()
        return (size.width(), size.height())

    def __init_camera(self):
        self.camera = QCamera(self.available_cameras[self.camera_id])
        self.camera.setCaptureMode(QCamera.CaptureViewfinder)
        self.camera.setViewfinder(self.viewfinder)

        self.probe = QtMultimedia.QVideoProbe(self.camera)
        self.probe.videoFrameProbed.connect(self.process_frame)
        self.probe.setSource(self.camera)

    def add_source(self, source, func=None, size=None):
        self.sources[source] = [func or self.process_pixmap, size]

    def process_pixmap(self, image, size):
        pixmap = QPixmap.fromImage(image)
        if size is not None:
            pixmap = pixmap.scaled(*size)
        return pixmap

    def process_sources(self, frame):
        for source, (process_pixmap, size) in self.sources.items():
            if size is None:
                size = frame.image().size()
                size = (size.width(), size.height())

            pixmap = process_pixmap(frame.image(), size)
            source.setPixmap(pixmap)

    def process_frame(self, frame):
        QApplication.processEvents()
        if frame.isValid():
            self.process_sources(frame)

    def get_available_cameras(self):
        return QCameraInfo.availableCameras()

    def change_camera_id(self, camera_id: int):
        self.camera_id = camera_id
        self.available_cameras = self.get_available_cameras()
        if not self.available_cameras:
            print("No camera found.")
            sys.exit()

        self.__init_camera()

    def start(self):
        self.camera.start()

    def stop(self):
        self.camera.stop()


class LabelCamera(QWidget):
    def __init__(self, camera_id=0, size=(100, 100), parent=None):
        QWidget.__init__(self, parent)
        self.layout = QVBoxLayout(self)
        self.camera_label = QLabel()
        self.size = size
        self.camera = Camera(camera_id)
        self.set_process_pixmap(None)
        self.resize_camera_label()

        self.layout.addWidget(self.camera_label)

    def get_available_cameras(self):
        return self.camera.get_available_cameras()

    def resize_camera_label(self):
        size = self.size
        if size is None:
            size = self.camera.get_size_or_camera_size()
        self.camera_label.resize(*size)

    def change_camera_id(self, camera_id: int):
        self.camera.change_camera_id(camera_id)
        self.start_camera()

    def start_camera(self):
        self.camera.start()

    def stop_camera(self):
        self.camera.stop()

    def set_process_pixmap(self, func):
        self.camera.add_source(self.camera_label, func, self.size)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Window size
        self.SIZE = 300
        self.resize(self.SIZE, self.SIZE)

        self.camera_widget = LabelCamera(
            camera_id=0, size=(self.SIZE, self.SIZE), parent=self
        )
        self.camera_widget.set_process_pixmap(
            lambda image, size: mask_image(image, size[0])
        )

        self.setCentralWidget(self.camera_widget)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.is_camera_show = False
        self.show_or_hide_camera()

        self.__init_setting_window()
        self.__init_systray()

    def __init_setting_window(self):
        self.setting_window = SettingsWindow()

    def __init_systray(self):
        self.trayIcon = SystemTrayIcon(
            QtGui.QIcon(str(config.RESOURCES_FOLDER / "tray_icon.xpm")), app
        )
        self.trayIcon.exitAction.triggered.connect(self.close)
        self.trayIcon.showOrHideAction.triggered.connect(self.show_or_hide_camera)
        self.trayIcon.settingsAction.triggered.connect(self.setting_window.show)
        self.trayIcon.show()

    def show_or_hide_camera(self):
        if self.is_camera_show:
            self.camera_widget.stop_camera()
            self.hide()
        else:
            self.camera_widget.start_camera()
            self.show()

        self.is_camera_show = not self.is_camera_show


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("Kolo-Face")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
