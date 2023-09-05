import sys
import typing

from PyQt5 import QtCore, QtMultimedia, QtGui
from PyQt5.Qt import Qt, QImage, QPainter, QBrush, QRect, QWindow, QPixmap
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QWidget

import config
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


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = settings_control_panel_ui.Ui_Form()
        self.ui.setupUi(self)


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)
        menu = QMenu()
        self.settingsAction = menu.addAction("Settings")
        self.showOrHideAction = menu.addAction("Show/Hide")
        self.exitAction = menu.addAction("Exit")
        self.setContextMenu(menu)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Window size
        self.SIZE = 300
        self.resize(self.SIZE, self.SIZE)

        self.available_cameras = QCameraInfo.availableCameras()
        if not self.available_cameras:
            print("No camera found.")
            sys.exit()

        self.camera = QCamera(self.available_cameras[1])
        self.camera.setCaptureMode(QCamera.CaptureViewfinder)
        self.viewfinder = QCameraViewfinder()

        self.probe = QtMultimedia.QVideoProbe(self)
        self.probe.videoFrameProbed.connect(self.process_frame)
        self.probe.setSource(self.camera)

        self.camera_label = QLabel()
        self.camera_label.resize(self.SIZE, self.SIZE)

        self.setCentralWidget(self.camera_label)
        self.camera.setViewfinder(self.viewfinder)

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
            self.stop_camera()
            self.hide()
        else:
            self.start_camera()
            self.show()

        self.is_camera_show = not self.is_camera_show

    def start_camera(self):
        self.camera.start()

    def stop_camera(self):
        self.camera.stop()

    def process_frame(self, frame):
        QApplication.processEvents()
        if frame.isValid():
            pixmap = mask_image(frame.image(), self.SIZE)
            self.camera_label.setPixmap(pixmap)

    def closeEvent(self, event):
        if self.probe.isActive():
            self.probe.videoFrameProbed.disconnect(self.process_frame)
            self.probe.deleteLater()
        self.camera.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("Kolo-Face")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
