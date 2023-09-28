import sys
import typing
import numpy as np

from PyQt5 import QtCore, QtMultimedia, QtGui, QtWidgets
from PyQt5.Qt import (
    Qt,
    QImage,
    QPainter,
    QBrush,
    QRect,
    QWindow,
    QPixmap,
    QPointF,
    QRectF,
    QSize,
)
from PyQt5.QtGui import QCursor, QColor, QPen
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsSceneHoverEvent, QWidget
import configparser

import config
from services.singleton import SingletonMeta
from services.callbacks import Callbacks
import ui.settings_control_panel as settings_control_panel_ui


def vector_projection(base_vector, projecting_vector):
    A = np.array(projecting_vector)
    B = np.array(base_vector)
    dot_product = np.dot(A, B)
    length_squared = np.dot(B, B)
    projection = (dot_product / length_squared) * B
    return projection


def mask_image(image, size, rect):
    # Load image
    # image = QImage.fromData(imgdata, imgtype)

    # convert image to 32-bit ARGB (adds an alpha
    # channel ie transparency factor):
    # image.convertToFormat(QImage.Format_ARGB32)

    # # Crop image to a square:
    # imgsize = min(image.width(), image.height())
    # rect = QRect(
    #     (image.width() - imgsize) // 2,
    #     (image.height() - imgsize) // 2,
    #     imgsize,
    #     imgsize,
    # )
    rect = QRect(
        int(rect.x()),
        int(rect.y()),
        int(rect.width()),
        int(rect.height()),
    )

    image = image.copy(rect)

    # Create the output image with the same dimensions
    # and an alpha channel and make it completely transparent:
    out_img = QImage(rect.width(), rect.height(), QImage.Format_ARGB32)
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
    painter.drawEllipse(0, 0, rect.width(), rect.height())

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


# class Config(metaclass=SingletonMeta):
#     def __init__(self, config_file=config.CONFIG_FILE):
#         self.config_file = config_file

#         self.config = configparser.ConfigParser()
#         # self.put_data_to_config(self.size, self.camera_id)

#     def __init_attribute(self, attribute_name, attribute_type):
#         self.__setattr__(attribute_name, property())
#         attr = self.__getattribute__(attribute_name)
#         attr = property(
#             fget=self.__generate_attribute_getter(attribute_name, ),
#             fset=self.__generate_attribute_setter(attribute_name, ),
#             doc=f"The radius {attribute_name}."
#         )
#         property().setter

#     def __generate_attribute_setter(attribute_name):
#         self.config

#     @property
#     def size(self):
#         ...

#     @size.setter
#     def size(self):
#         ...

#     def upload(self, size, camera_id):
#         self.put_data_to_config(size, camera_id)

#         with self.config_file.open("w") as configfile:
#             self.config.write(configfile)

#     def load(self):
#         self.config.read(self.config_file)
#         self.camera_id = int(self.config["DEFAULT"]["camera_id"])
#         self.size = int(self.config["DEFAULT"]["size"])


class Config(metaclass=SingletonMeta):
    def __init__(self, config_file=config.CONFIG_FILE):
        self.config_file = config_file
        self.camera_id = 0
        self.size = 300

        self.config = configparser.ConfigParser()
        self.put_data_to_config(self.size, self.camera_id)

    def put_data_to_config(self, size, camera_id):
        self.config["DEFAULT"] = {
            "camera_id": camera_id,
            "size": size,
        }

    def upload(self, size, camera_id):
        self.put_data_to_config(size, camera_id)

        with self.config_file.open("w") as configfile:
            self.config.write(configfile)

    def load(self):
        # try:
        self.config.read(self.config_file)
        self.camera_id = int(self.config["DEFAULT"]["camera_id"])
        self.size = int(self.config["DEFAULT"]["size"])


class SettingsPanelWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.ui = settings_control_panel_ui.Ui_Form()
        self.ui.setupUi(self)


class CameraPixmapItem(QGraphicsPixmapItem):
    def resize(self, *args, **kwargs):
        ...


class CameraResizeWidget(QGraphicsItem):
    ...


class QGraphicsItemPositionMixin(object):
    @property
    def position(self):
        pos = self.scenePos()
        return (pos.x(), pos.y())

    @position.setter
    def position(self, position):
        self.setPos(*position)


class CameraResizeMarkerWidget(QGraphicsItem, QGraphicsItemPositionMixin):
    MARKER_SIZE = 30

    def __init__(
        self,
        parent=None,
        position=None,
        orientation=0,
        is_move_diagonal=True,
        *args,
        **kwargs,
    ):
        super().__init__(parent, *args, **kwargs)
        self.setAcceptHoverEvents(True)

        self.on_move = Callbacks()

        self.position = position or (0, 0)
        self.is_move_diagonal = is_move_diagonal
        self.orientation = orientation
        self.is_marker_can_move = lambda: True
        self.border_pen = QPen(Qt.white)
        self.border_pen.setWidth(3)

    def boundingRect(self):
        return QRectF(0, 0, self.MARKER_SIZE, self.MARKER_SIZE)

    def paint(self, painter, option, widget):
        painter.setPen(self.border_pen)

        draw_vertical_line_1 = lambda: painter.drawLine(0, 0, 0, self.MARKER_SIZE)
        draw_vertical_line_2 = lambda: painter.drawLine(
            self.MARKER_SIZE, self.MARKER_SIZE, self.MARKER_SIZE, 0
        )

        draw_horizontal_line_1 = lambda: painter.drawLine(0, 0, self.MARKER_SIZE, 0)
        draw_horizontal_line_2 = lambda: painter.drawLine(
            0, self.MARKER_SIZE, self.MARKER_SIZE, self.MARKER_SIZE
        )

        if self.orientation == 0:
            draw_vertical_line_1()
            draw_horizontal_line_1()

        elif self.orientation == 1:
            draw_vertical_line_2()
            draw_horizontal_line_1()

        elif self.orientation == 2:
            draw_vertical_line_2()
            draw_horizontal_line_2()

        elif self.orientation == 3:
            draw_vertical_line_1()
            draw_horizontal_line_2()

    def hoverEnterEvent(self, event):
        cursor = QCursor(Qt.OpenHandCursor)
        QApplication.instance().setOverrideCursor(cursor)

    def hoverLeaveEvent(self, event):
        QApplication.instance().restoreOverrideCursor()

    def mouseMoveEvent(self, event):
        if not self.is_marker_can_move():
            return

        new_pos = event.scenePos()
        if self.is_move_diagonal:
            x, y = new_pos.x(), new_pos.y()
            old_pos = self.position
            moved_vector = (x - old_pos[0], y - old_pos[1])

            match self.orientation:
                case 0 | 2:
                    new_pos = vector_projection((1, 1), moved_vector)
                case 1 | 3:
                    new_pos = vector_projection((-1, 1), moved_vector)
                case _:
                    ...

            new_pos += np.array(old_pos)

        self.position = new_pos
        self.on_move.send(self.orientation)

        if not self.is_marker_can_move():
            self.position = old_pos

        self.on_move.send(self.orientation)

    # We must override these or else the default implementation prevents
    #  the mouseMoveEvent() override from working.
    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass


class CameraResizeRectWidget(QGraphicsItem, QGraphicsItemPositionMixin):
    MARKER_DISTANCE = 100

    def __init__(self, border_rect: QRectF) -> None:
        super().__init__()
        self.setAcceptHoverEvents(True)

        self.border_rect: QRectF = border_rect
        size = min(self.border_rect.width(), self.border_rect.height())
        dx = self.border_rect.x() + (self.border_rect.width() - size) // 2
        dy = self.border_rect.y() + (self.border_rect.height() - size) // 2

        self.size = (size, size)

        marker_size = CameraResizeMarkerWidget.MARKER_SIZE
        self.marker_0 = CameraResizeMarkerWidget(
            parent=self, orientation=0, position=(dx, dy)
        )
        self.marker_0.on_move.add(self.update_size_with_marker)
        self.marker_0.is_marker_can_move = self.is_marker_can_move

        self.marker_1 = CameraResizeMarkerWidget(
            parent=self, orientation=1, position=(dx + self.size[0] - marker_size, dy)
        )
        self.marker_1.on_move.add(self.update_size_with_marker)
        self.marker_1.is_marker_can_move = self.is_marker_can_move

        self.marker_2 = CameraResizeMarkerWidget(
            parent=self,
            orientation=2,
            position=(dx + self.size[0] - marker_size, dy + self.size[1] - marker_size),
        )
        self.marker_2.on_move.add(self.update_size_with_marker)
        self.marker_2.is_marker_can_move = self.is_marker_can_move

        self.marker_3 = CameraResizeMarkerWidget(
            parent=self, orientation=3, position=(dx, dy + self.size[1] - marker_size)
        )
        self.marker_3.on_move.add(self.update_size_with_marker)
        self.marker_3.is_marker_can_move = self.is_marker_can_move

        self.bg_color = QColor(50, 50, 50, 150)
        self.border_pen = QPen(Qt.white)
        self.border_pen.setWidth(1)
        self.is_can_drag = False
        self._dx = 0
        self._dy = 0

    def is_marker_can_move(self) -> bool:
        rect = self.boundingRect()
        is_rect_not_to_small = (
            rect.width() > self.MARKER_DISTANCE and rect.height() > self.MARKER_DISTANCE
        )
        is_rect_out_of_bounds = self.border_rect.intersected(rect) != rect
        return is_rect_not_to_small and not is_rect_out_of_bounds

    def update_size_with_marker(self, moved_marker_orientation):
        def update_markers_position(
            changed_marker, marker_for_x_update, marker_for_y_update
        ):
            new_pos = changed_marker.position

            # update y
            marker_for_y_update.position = (
                marker_for_y_update.position[0],
                new_pos[1],
            )
            # update x
            marker_for_x_update.position = (
                new_pos[0],
                marker_for_x_update.position[1],
            )

        match moved_marker_orientation:
            case 0:
                update_markers_position(
                    changed_marker=self.marker_0,
                    marker_for_x_update=self.marker_3,
                    marker_for_y_update=self.marker_1,
                )
            case 1:
                update_markers_position(
                    changed_marker=self.marker_1,
                    marker_for_x_update=self.marker_2,
                    marker_for_y_update=self.marker_0,
                )
            case 2:
                update_markers_position(
                    changed_marker=self.marker_2,
                    marker_for_x_update=self.marker_1,
                    marker_for_y_update=self.marker_3,
                )
            case 3:
                update_markers_position(
                    changed_marker=self.marker_3,
                    marker_for_x_update=self.marker_0,
                    marker_for_y_update=self.marker_2,
                )
            case _:
                ...

        # self.scene().
        QtGui.QGuiApplication.processEvents()

    def boundingRect(self):
        start_point = self.marker_0.position
        end_point = self.marker_2.position

        w_h = list(
            map(
                lambda a_b: a_b[1] - a_b[0] + self.marker_2.MARKER_SIZE,
                zip(start_point, end_point),
            )
        )
        return QRectF(*start_point, *w_h)

    def paint(self, painter, option, widget):
        rect = self.boundingRect()
        w = int(rect.width())
        h = int(rect.height())
        x = int(rect.x())
        y = int(rect.y())

        b_w = int(self.border_rect.width())
        b_h = int(self.border_rect.height())
        b_x = int(self.border_rect.x())
        b_y = int(self.border_rect.y())

        painter.fillRect(b_x, b_y, x - b_x, b_h, self.bg_color)
        painter.fillRect(x + w, b_y, b_w - (x - b_x + w), b_h, self.bg_color)

        painter.fillRect(x, b_y, w, y - b_y, self.bg_color)
        painter.fillRect(x, y + h, w, b_h - (y + h - b_y), self.bg_color)

        painter.setPen(self.border_pen)
        painter.drawRect(self.boundingRect())
        painter.drawEllipse(self.boundingRect())

    def hoverEnterEvent(self, event):
        pass

    def hoverMoveEvent(self, event):
        rect = self.boundingRect()
        x_c = rect.x() + rect.width() / 2
        y_c = rect.y() + rect.height() / 2

        pos = event.pos()
        x, y = pos.x() - x_c, pos.y() - y_c

        self._dx = pos.x() - rect.x()
        self._dy = pos.y() - rect.y()

        prev_is_can_drag = self.is_can_drag
        self.is_can_drag = x * x + y * y <= (rect.width() / 2) ** 2

        if self.is_can_drag and not prev_is_can_drag:
            cursor = QCursor(Qt.OpenHandCursor)
            QApplication.instance().setOverrideCursor(cursor)
        elif not self.is_can_drag and prev_is_can_drag:
            QApplication.instance().restoreOverrideCursor()

        return super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        QApplication.instance().restoreOverrideCursor()
        self.is_can_drag = False

    def move_markers(self, position):
        rect = self.boundingRect()

        self.marker_0.position = (position[0], position[1])
        self.marker_1.position = (
            position[0] + rect.width() - self.marker_2.MARKER_SIZE,
            position[1],
        )
        self.marker_2.position = (
            position[0] + rect.width() - self.marker_2.MARKER_SIZE,
            position[1] + rect.height() - self.marker_2.MARKER_SIZE,
        )
        self.marker_3.position = (
            position[0],
            position[1] + rect.height() - self.marker_2.MARKER_SIZE,
        )

    def mouseMoveEvent(self, event):
        if not self.is_can_drag:  # not self.is_marker_can_move()
            return

        new_pos = event.scenePos()
        x, y = new_pos.x(), new_pos.y()
        old_rect = self.boundingRect()

        self.move_markers((x - self._dx, y - self._dy))

        if not self.is_marker_can_move():
            # x_c = old_rect.x() + old_rect.width() / 2
            # y_c = old_rect.y() + old_rect.height() / 2
            old_x, old_y = old_rect.x(), old_rect.y()

            self.move_markers((old_x, old_y))

    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass


class SettingsWindow(QWidget):
    size_changed = QtCore.pyqtSignal(int)

    def __init__(self, default_size, default_camera_id):
        super().__init__()
        self.config = Config()
        self.settings_panel = SettingsPanelWidget(self)
        self.layout = QVBoxLayout(self)

        self.camera_image = CameraPixmapItem()
        # self.camera_image.set
        # self.setAcceptHoverEvents(True)
        self.camera = CameraSource(
            camera_id=default_camera_id,
            size=None,
            camera_source_widget=self.camera_image,
            parent=self,
            add_to_layout=False,
        )
        self.camera.camera.on_camera_size_changed.add(self.change_camera_resize_item)
        # self.camera

        self.camera_resize_widget = CameraResizeWidget()

        self.scene = QGraphicsScene()
        self.view = QGraphicsView()
        self.view.setScene(self.scene)

        self.scene.addItem(self.camera_image)
        self.scene.addItem(self.camera_resize_widget)
        # self.scene.focusItem()
        self.camera_image.setFocus(True)

        self.camera_resize_item = None

        self.layout.addWidget(self.view)
        self.layout.addWidget(self.settings_panel)
        self.settings_panel.ui.cameras_list.currentIndexChanged.connect(
            self.change_camera
        )
        self.available_cameras = []

        self.settings_panel.ui.size_input.setValue(default_size)
        self.settings_panel.ui.size_input.valueChanged.connect(self.change_size)
        self.settings_panel.ui.save_button.clicked.connect(self.save_config)

        self.camera.start_camera()

    def get_camera_resize_rect(self):
        return self.camera_resize_item.boundingRect()

    def change_size(self, size: int):
        self.size_changed.emit(size)

    def save_config(self):
        self.config.upload(
            size=self.settings_panel.ui.size_input.value(),
            camera_id=self.camera_id,
        )

    def change_camera(self, camera_id):
        self.camera_id = camera_id
        self.camera.change_camera_id(camera_id)
        # self.camera.resize_camera_source_widget()

        # size = self.camera.size()
        # size = self.camera.camera.get_size_or_camera_size()
        # size = self.camera_image.pixmap().size()
        # print(size)

    def change_camera_resize_item(self, size):
        if self.camera_resize_item is not None:
            self.scene.removeItem(self.camera_resize_item)

        self.camera_resize_item = CameraResizeRectWidget(
            border_rect=QRectF(0, 0, size.width(), size.height())
            # border_rect=QRectF(QPointF(0, 0), size)
        )
        self.scene.addItem(self.camera_resize_item)

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

        self._frame_size = QSize()
        self.on_camera_size_changed = Callbacks()

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
            frame_size = frame.size()
            if self._frame_size != frame_size:
                self.on_camera_size_changed.send(frame_size)
                self._frame_size = frame_size

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


class CameraSource(QWidget):
    def __init__(
        self,
        camera_id=0,
        size=(100, 100),
        camera_source_widget=None,
        add_to_layout=True,
        parent=None,
    ):
        QWidget.__init__(self, parent)
        self.layout = QVBoxLayout(self)
        self.camera_source_widget = camera_source_widget or QLabel()
        self._size = size
        self._process_pixmap_func = None
        self.camera = Camera(camera_id)

        self.resize_camera_source_widget()

        if add_to_layout:
            self.layout.addWidget(self.camera_source_widget)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = size

    def get_available_cameras(self):
        return self.camera.get_available_cameras()

    def resize_camera_source_widget(self):
        size = self.size
        if size is None:
            size = self.camera.get_size_or_camera_size()
        self.camera_source_widget.resize(*size)

        # for update size in Camera.sources
        self.set_process_pixmap(self._process_pixmap_func)

    def change_camera_id(self, camera_id: int):
        self.camera.change_camera_id(camera_id)
        self.start_camera()

    def start_camera(self):
        self.camera.start()

    def stop_camera(self):
        self.camera.stop()

    def set_process_pixmap(self, func):
        self._process_pixmap_func = func
        self.camera.add_source(self.camera_source_widget, func, self.size)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.config = Config()
        self.config.load()

        self.SIZE = self.config.size
        self.camera_id = self.config.camera_id

        self.resize(self.SIZE, self.SIZE)

        self.camera_widget = CameraSource(
            camera_id=self.camera_id, size=(self.SIZE, self.SIZE), parent=self
        )
        self.camera_widget.set_process_pixmap(self.circle_image)

        self.setCentralWidget(self.camera_widget)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.is_camera_show = False
        self.show_or_hide_camera()

        self.__init_setting_window()
        self.__init_systray()

        self.startPos = None
        QtWidgets.QApplication.instance().installEventFilter(self)

    def eventFilter(self, source, event):
        if (
            event.type() == QtCore.QEvent.MouseButtonPress
            and event.button() == QtCore.Qt.LeftButton
        ):
            self.startPos = event.pos()
            return True
        elif event.type() == QtCore.QEvent.MouseMove and self.startPos is not None:
            self.move(self.pos() + event.pos() - self.startPos)
            return True
        elif (
            event.type() == QtCore.QEvent.MouseButtonRelease
            and self.startPos is not None
        ):
            self.startPos = None
            return True
        return super(MainWindow, self).eventFilter(source, event)

    def __init_setting_window(self):
        self.setting_window = SettingsWindow(self.SIZE, self.camera_id)
        self.setting_window.size_changed.connect(self.change_size)

    def circle_image(self, image, size):
        rect = self.setting_window.get_camera_resize_rect()
        return mask_image(image, size[0], rect)

    def change_size(self, size):
        self.SIZE = size
        self.camera_widget.size = (self.SIZE, self.SIZE)
        self.camera_widget.resize_camera_source_widget()

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

    def closeEvent(self, a0) -> None:
        self.setting_window.close()
        return super().closeEvent(a0)


if __name__ == "__main__":
    app = QApplication([])
    app.setApplicationName("Kolo-Face")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
