# ---- ui_app.py (archivo completo corregido) ----
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QGraphicsScene, QGraphicsView, QFrame, QSizePolicy,
    QMessageBox, QRadioButton, QButtonGroup, QGridLayout, QGroupBox, QCheckBox,
    QFileDialog, QGraphicsItem
)
from PySide6.QtGui import (
    QPixmap, QImage, QColor, QPen, QPainter, QTransform, QIcon
)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PIL import Image
import fitz  # PyMuPDF

from utils import (
    cm_to_pixels, pixels_to_cm, DEFAULT_DPI,
    calculate_print_cost, PRINT_COSTS
)
from styles import get_stylesheet, get_theme_colors

def create_section_groupbox(title):
    group_box = QGroupBox(title)
    group_box.setObjectName("SectionGroupBox")
    layout = QVBoxLayout()
    group_box.setLayout(layout)
    return group_box, layout

class ImageCanvasApp(QWidget):
    def __init__(self, initial_theme="light"):
        super().__init__()
        self.current_theme = initial_theme
        self.original_image_pil = None
        self.current_display_image_pil = None
        self.canvas_width_px = 0
        self.canvas_height_px = 0
        self.image_position_on_canvas_px = {'x': 0, 'y': 0}
        self.current_image_mode = "fit_to_canvas"
        self.preview_scale_factor = 1.0
        self.last_calculated_non_white_percentage = 0.0
        self.current_image_rotation_angle = 0
        self.drag_start_pos = QPointF()
        self.is_dragging_image = False
        self.current_image_item = None
        self.current_canvas_item = None
        self._large_canvas_warned = False

        self.init_ui()
        self.apply_stylesheet(self.current_theme)
        self.calculate_and_display_cost()

    def apply_theme(self, theme):
        self.current_theme = theme
        self.setStyleSheet(get_stylesheet(theme))

    def init_ui(self, initial_theme="light"):
        self.current_theme = initial_theme
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # --- Panel de Control ---
        self.controls_frame = QFrame(self)
        self.controls_frame.setObjectName("ControlsFrame")
        self.controls_frame.setFrameShape(QFrame.StyledPanel)
        self.controls_layout = QVBoxLayout()
        self.controls_layout.setContentsMargins(10, 10, 10, 10)
        self.controls_layout.setSpacing(1)
        self.controls_frame.setLayout(self.controls_layout)

        # Sección: Creación de Lienzo
        canvas_group_box, canvas_section_layout = create_section_groupbox("🖼️ Crear Lienzo (cm)")
        canvas_grid_layout = QGridLayout()
        canvas_grid_layout.setSpacing(10)
        canvas_section_layout.addLayout(canvas_grid_layout)
        canvas_grid_layout.addWidget(QLabel("Ancho:"), 0, 0)
        self.width_entry_cm = QLineEdit()
        self.width_entry_cm.setPlaceholderText("Ej: 70")
        self.width_entry_cm.returnPressed.connect(self.create_canvas)
        canvas_grid_layout.addWidget(self.width_entry_cm, 0, 1)
        canvas_grid_layout.addWidget(QLabel("Alto:"), 1, 0)
        self.height_entry_cm = QLineEdit()
        self.height_entry_cm.setPlaceholderText("Ej: 100")
        self.height_entry_cm.returnPressed.connect(self.create_canvas)
        canvas_grid_layout.addWidget(self.height_entry_cm, 1, 1)

        self.create_canvas_btn = QPushButton("🆕 Crear Lienzo")
        self.create_canvas_btn.setObjectName("create_canvas_btn")
        self.create_canvas_btn.clicked.connect(self.create_canvas)
        canvas_section_layout.addWidget(self.create_canvas_btn)
        self.controls_layout.addWidget(canvas_group_box)

        # Sección: Cargar Imagen/PDF
        load_image_group_box, load_image_section_layout = create_section_groupbox("📂 Cargar Imagen / PDF")
        self.load_image_btn = QPushButton("📂 Cargar Archivo")
        self.load_image_btn.setObjectName("load_image_btn")
        self.load_image_btn.clicked.connect(self.load_image_or_pdf)
        load_image_section_layout.addWidget(self.load_image_btn)
        self.original_image_info_label = QLabel("📏 Tamaño Real: N/A")
        load_image_section_layout.addWidget(self.original_image_info_label)
        self.controls_layout.addWidget(load_image_group_box)

        # Sección: Ajustar Imagen
        adjust_size_group_box, adjust_size_section_layout = create_section_groupbox("⚙️ Ajustar Imagen")
        self.size_mode_group = QButtonGroup(self)

        self.radio_fit_to_canvas = QRadioButton("🔄 Ajustar a Lienzo (Mantener Aspecto)")
        self.radio_fit_to_canvas.setChecked(True)
        self.radio_fit_to_canvas.toggled.connect(self.toggle_custom_size_entries)
        self.radio_fit_to_canvas.toggled.connect(self.set_image_mode_and_resize)
        adjust_size_section_layout.addWidget(self.radio_fit_to_canvas)
        self.size_mode_group.addButton(self.radio_fit_to_canvas)

        self.radio_real_size = QRadioButton("📏 Tamaño Real de la Imagen")
        self.radio_real_size.toggled.connect(self.set_image_mode_and_resize)
        adjust_size_section_layout.addWidget(self.radio_real_size)
        self.size_mode_group.addButton(self.radio_real_size)

        self.radio_custom_size = QRadioButton("✏️ Tamaño Personalizado (cm)")
        self.radio_custom_size.toggled.connect(self.toggle_custom_size_entries)
        self.radio_custom_size.toggled.connect(self.set_image_mode_and_resize)
        adjust_size_section_layout.addWidget(self.radio_custom_size)
        self.size_mode_group.addButton(self.radio_custom_size)

        self.custom_size_layout = QGridLayout()
        self.custom_size_layout.setSpacing(10)
        self.maintain_aspect_ratio_checkbox = QCheckBox("📐 Mantener Relación de Aspecto")
        self.maintain_aspect_ratio_checkbox.setChecked(True)
        self.maintain_aspect_ratio_checkbox.toggled.connect(self.set_image_mode_and_resize)
        self.custom_size_layout.addWidget(self.maintain_aspect_ratio_checkbox, 0, 0, 1, 2)
        self.custom_size_layout.addWidget(QLabel("Ancho:"), 1, 0)
        self.custom_width_entry_cm = QLineEdit()
        self.custom_width_entry_cm.setPlaceholderText("Ancho en cm")
        self.custom_width_entry_cm.returnPressed.connect(self.set_image_mode_and_resize)
        self.custom_size_layout.addWidget(self.custom_width_entry_cm, 1, 1)
        self.custom_size_layout.addWidget(QLabel("Alto:"), 2, 0)
        self.custom_height_entry_cm = QLineEdit()
        self.custom_height_entry_cm.setPlaceholderText("Alto en cm")
        self.custom_height_entry_cm.returnPressed.connect(self.set_image_mode_and_resize)
        self.custom_size_layout.addWidget(self.custom_height_entry_cm, 2, 1)
        self.custom_width_entry_cm.textChanged.connect(self.resize_image_on_canvas_if_valid)
        self.custom_height_entry_cm.textChanged.connect(self.resize_image_on_canvas_if_valid)
        adjust_size_section_layout.addLayout(self.custom_size_layout)
        self.toggle_custom_size_entries()

        # Rotación
        rotation_layout = QHBoxLayout()
        rotate_left_btn = QPushButton("↩️ Izquierda (90°)")
        rotate_left_btn.clicked.connect(self.rotate_image_left)
        rotation_layout.addWidget(rotate_left_btn)
        rotate_right_btn = QPushButton("↪️ Derecha (90°)")
        rotate_right_btn.clicked.connect(self.rotate_image_right)
        rotation_layout.addWidget(rotate_right_btn)
        adjust_size_section_layout.addLayout(rotation_layout)
        self.controls_layout.addWidget(adjust_size_group_box)

        # Sección: Análisis de Píxeles
        pixel_analysis_group_box, pixel_analysis_section_layout = create_section_groupbox("🔍 Análisis de Píxeles")
        self.pixel_result_label = QLabel("📊 Resultado: N/A")
        pixel_analysis_section_layout.addWidget(self.pixel_result_label)
        self.analyze_pixels_btn = QPushButton("🔍 Calcular Píxeles No Blancos y Costo")
        self.analyze_pixels_btn.setObjectName("analyze_pixels_btn")
        self.analyze_pixels_btn.clicked.connect(self.calculate_non_white_pixels_and_update_cost)
        pixel_analysis_section_layout.addWidget(self.analyze_pixels_btn)
        self.controls_layout.addWidget(pixel_analysis_group_box)

        # Sección: Cálculo de Costos
        cost_calc_group_box, cost_calc_section_layout = create_section_groupbox("💰 Cálculo de Costos")
        self.selected_print_type_label = QLabel("📄 Tipo de Pliego: N/A")
        cost_calc_section_layout.addWidget(self.selected_print_type_label)
        self.cost_result_label = QLabel("💵 Costo Estimado: N/A")
        cost_calc_section_layout.addWidget(self.cost_result_label)
        self.controls_layout.addWidget(cost_calc_group_box)

        # Botones finales
        self.controls_layout.addStretch(1)
        self.controls_frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.controls_frame.setFixedWidth(350)

        self.reset_btn = QPushButton("🔄 Reiniciar Todo")
        self.reset_btn.setObjectName("ResetButton")
        self.reset_btn.clicked.connect(self.reset_all)
        self.controls_layout.addWidget(self.reset_btn)

        self.print_btn = QPushButton("🖨️ Imprimir Lienzo")
        self.print_btn.setObjectName("print_btn")
        self.print_btn.clicked.connect(self.print_canvas)
        self.controls_layout.addWidget(self.print_btn)

        # --- Área de Visualización ---
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view = QGraphicsView(self.graphics_scene)
        self.graphics_view.setObjectName("GraphicsView")
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        self.graphics_view.setMouseTracking(True)

        # Conexiones para arrastrar la imagen
        self.graphics_view.mousePressEvent = self.view_mouse_press_event
        self.graphics_view.mouseMoveEvent = self.view_mouse_move_event
        self.graphics_view.mouseReleaseEvent = self.view_mouse_release_event

        main_layout.addWidget(self.controls_frame)
        main_layout.addWidget(self.graphics_view)
        self.setLayout(main_layout)
        self.graphics_view.setSceneRect(0, 0, 1, 1)

    def create_canvas(self):
        try:
            width_cm = float(self.width_entry_cm.text())
            height_cm = float(self.height_entry_cm.text())

            if width_cm <= 0 or height_cm <= 0:
                self.show_message_box("Error de Entrada", "El ancho y el alto deben ser mayores que cero.", QMessageBox.Warning)
                return

            self.canvas_width_px = cm_to_pixels(width_cm)
            self.canvas_height_px = cm_to_pixels(height_cm)

            print(f"\nLienzo creado: {width_cm}x{height_cm} cm ({self.canvas_width_px}x{self.canvas_height_px} px)")

            self.redraw_canvas_and_image()
            self.show_message_box("Lienzo Creado", 
                                f"Lienzo de {width_cm:.2f} cm x {height_cm:.2f} cm creado correctamente.", 
                                QMessageBox.Information)

            if self.original_image_pil:
                self.calculate_non_white_pixels_and_update_cost()
            else:
                self.pixel_result_label.setText("Resultado: N/A")
                self.calculate_and_display_cost()

            self._large_canvas_warned = False

        except ValueError:
            self.show_message_box("Error de Entrada", 
                               "Por favor, ingrese valores numéricos válidos para el ancho y el alto.", 
                               QMessageBox.Critical)
        except Exception as e:
            self.show_message_box("Error", f"Ocurrió un error al crear el lienzo: {e}", QMessageBox.Critical)

    def show_message_box(self, title, message, icon=QMessageBox.Information, buttons=QMessageBox.Ok):
        msg_box = QMessageBox(self)
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(buttons)
        return msg_box.exec()

    def apply_stylesheet(self, theme):
        self.current_theme = theme
        self.setStyleSheet(get_stylesheet(theme))
        theme_colors = get_theme_colors(theme)
        self.graphics_view.setBackgroundBrush(QColor(theme_colors['graphics_view_bg']))
        self.redraw_canvas_and_image()

    def load_image_or_pdf(self):
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Archivos de Imagen/PDF (*.png *.jpg *.jpeg *.bmp *.gif *.pdf)")
        file_dialog.setFileMode(QFileDialog.ExistingFile)

        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                file_path = selected_files[0]
                self.current_image_rotation_angle = 0
                if file_path.lower().endswith('.pdf'):
                    self.load_pdf(file_path)
                else:
                    self.load_image(file_path)

    def load_image(self, file_path):
        try:
            img = Image.open(file_path)
            img.load()
            self.original_image_pil = img.convert("RGBA") if img.mode != "RGBA" else img

            original_width_cm = pixels_to_cm(self.original_image_pil.width)
            original_height_cm = pixels_to_cm(self.original_image_pil.height)
            self.original_image_info_label.setText(
                f"Tamaño Real: {original_width_cm:.2f} cm x {original_height_cm:.2f} cm "
                f"({self.original_image_pil.width}x{self.original_image_pil.height} px)"
            )
            
            self.set_image_mode_and_resize()
            self.show_message_box(
                "Imagen Cargada", 
                f"'{os.path.basename(file_path)}' cargada exitosamente.", 
                QMessageBox.Information
            )
            self.calculate_non_white_pixels_and_update_cost()

        except Exception as e:
            self.show_message_box(
                "Error al Cargar Imagen", 
                f"No se pudo cargar la imagen: {e}", 
                QMessageBox.Critical
            )
            self.original_image_pil = None
            self.current_display_image_pil = None
            self.original_image_info_label.setText("Tamaño Real: N/A")
            self.redraw_canvas_and_image()
            self.calculate_and_display_cost()

    def load_pdf(self, file_path):
        try:
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                self.show_message_box("Error PDF", "El PDF no contiene páginas.", QMessageBox.Warning)
                doc.close()
                return

            page = doc.load_page(0)
            mat = fitz.Matrix(DEFAULT_DPI / 72.0, DEFAULT_DPI / 72.0)
            pix = page.get_pixmap(matrix=mat)
            doc.close()

            if pix.alpha:
                self.original_image_pil = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            else:
                self.original_image_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

            if self.original_image_pil:
                original_width_cm = pixels_to_cm(self.original_image_pil.width)
                original_height_cm = pixels_to_cm(self.original_image_pil.height)
                self.original_image_info_label.setText(
                    f"Tamaño Real: {original_width_cm:.2f} cm x {original_height_cm:.2f} cm "
                    f"({self.original_image_pil.width}x{self.original_image_pil.height} px)"
                )
                self.set_image_mode_and_resize()
                self.show_message_box(
                    "PDF Cargado",
                    f"La primera página del PDF '{os.path.basename(file_path)}' ha sido cargada.",
                    QMessageBox.Information
                )
                self.calculate_non_white_pixels_and_update_cost()
            else:
                self.show_message_box(
                    "Error PDF", 
                    "No se pudo procesar la primera página del PDF.", 
                    QMessageBox.Critical
                )

        except Exception as e:
            self.show_message_box(
                "Error al Cargar PDF", 
                f"No se pudo cargar o procesar el PDF: {e}", 
                QMessageBox.Critical
            )
            self.original_image_pil = None
            self.current_display_image_pil = None
            self.original_image_info_label.setText("Tamaño Real: N/A")
            self.redraw_canvas_and_image()
            self.calculate_and_display_cost()

    def resize_image_on_canvas_if_valid(self):
        QTimer.singleShot(50, self.set_image_mode_and_resize)

    def set_image_mode_and_resize(self):
        if not self.original_image_pil:
            return

        if self.radio_fit_to_canvas.isChecked():
            self.current_image_mode = "fit_to_canvas"
        elif self.radio_real_size.isChecked():
            self.current_image_mode = "real_size"
        elif self.radio_custom_size.isChecked():
            self.current_image_mode = "custom_size"

        self._perform_image_resize_and_position()

    def _perform_image_resize_and_position(self):
        if not self.original_image_pil or self.canvas_width_px <= 0 or self.canvas_height_px <= 0:
            return

        rotated_image_for_dims = self.original_image_pil.rotate(self.current_image_rotation_angle, expand=True)
        target_width_px = rotated_image_for_dims.width
        target_height_px = rotated_image_for_dims.height
        original_aspect_ratio = rotated_image_for_dims.width / rotated_image_for_dims.height

        if self.current_image_mode == "fit_to_canvas":
            canvas_aspect_ratio = self.canvas_width_px / self.canvas_height_px
            if original_aspect_ratio > canvas_aspect_ratio:
                target_width_px = self.canvas_width_px
                target_height_px = int(self.canvas_width_px / original_aspect_ratio)
            else:
                target_height_px = self.canvas_height_px
                target_width_px = int(self.canvas_height_px * original_aspect_ratio)

            self.image_position_on_canvas_px['x'] = (self.canvas_width_px - target_width_px) // 2
            self.image_position_on_canvas_px['y'] = (self.canvas_height_px - target_height_px) // 2

        elif self.current_image_mode == "real_size":
            target_width_px = rotated_image_for_dims.width
            target_height_px = rotated_image_for_dims.height
            self.image_position_on_canvas_px['x'] = (self.canvas_width_px - target_width_px) // 2
            self.image_position_on_canvas_px['y'] = (self.canvas_height_px - target_height_px) // 2

        elif self.current_image_mode == "custom_size":
            try:
                custom_width_cm_str = self.custom_width_entry_cm.text()
                custom_height_cm_str = self.custom_height_entry_cm.text()

                if not custom_width_cm_str and not custom_height_cm_str:
                    self.current_display_image_pil = rotated_image_for_dims.copy()
                    self.redraw_canvas_and_image()
                    return

                maintain_aspect = self.maintain_aspect_ratio_checkbox.isChecked()
                input_width_px = cm_to_pixels(float(custom_width_cm_str)) if custom_width_cm_str else 0
                input_height_px = cm_to_pixels(float(custom_height_cm_str)) if custom_height_cm_str else 0

                if maintain_aspect:
                    if input_width_px > 0 and not custom_height_cm_str:
                        target_width_px = input_width_px
                        target_height_px = int(input_width_px / original_aspect_ratio)
                    elif input_height_px > 0 and not custom_width_cm_str:
                        target_width_px = int(input_height_px * original_aspect_ratio)
                        target_height_px = input_height_px
                    elif input_width_px > 0 and input_height_px > 0:
                        target_width_px = input_width_px
                        target_height_px = int(input_width_px / original_aspect_ratio)
                else:
                    if input_width_px > 0:
                        target_width_px = input_width_px
                    if input_height_px > 0:
                        target_height_px = input_height_px

                if target_width_px <= 0 or target_height_px <= 0:
                    self.show_message_box(
                        "Error", 
                        "Ingrese valores de ancho y alto válidos para el tamaño personalizado.", 
                        QMessageBox.Warning
                    )
                    self.current_display_image_pil = rotated_image_for_dims.copy()
                    self.redraw_canvas_and_image()
                    return

            except ValueError:
                self.current_display_image_pil = rotated_image_for_dims.copy()
                self.redraw_canvas_and_image()
                return
            except Exception as e:
                self.show_message_box(
                    "Error de Tamaño Personalizado", 
                    f"Error: {e}", 
                    QMessageBox.Critical
                )
                return

        if target_width_px > 0 and target_height_px > 0:
            rotated_image_pil = self.original_image_pil.rotate(self.current_image_rotation_angle, expand=True)
            self.current_display_image_pil = rotated_image_pil.resize(
                (target_width_px, target_height_px), Image.Resampling.LANCZOS
            )
            self.image_position_on_canvas_px['x'] = (self.canvas_width_px - target_width_px) // 2
            self.image_position_on_canvas_px['y'] = (self.canvas_height_px - target_height_px) // 2
        else:
            self.current_display_image_pil = rotated_image_for_dims.copy()
            self.image_position_on_canvas_px = {'x': 0, 'y': 0}

        self.redraw_canvas_and_image()

    def rotate_image_left(self):
        if not self.original_image_pil:
            self.show_message_box(
                "No Image", 
                "Cargue una imagen primero para rotar.", 
                QMessageBox.Information
            )
            return
        self.current_image_rotation_angle = (self.current_image_rotation_angle - 90) % 360
        self.set_image_mode_and_resize()

    def rotate_image_right(self):
        if not self.original_image_pil:
            self.show_message_box(
                "No Image", 
                "Cargue una imagen primero para rotar.", 
                QMessageBox.Information
            )
            return
        self.current_image_rotation_angle = (self.current_image_rotation_angle + 90) % 360
        self.set_image_mode_and_resize()

    def toggle_custom_size_entries(self):
        is_custom = self.radio_custom_size.isChecked()
        self.custom_width_entry_cm.setEnabled(is_custom)
        self.custom_height_entry_cm.setEnabled(is_custom)
        self.maintain_aspect_ratio_checkbox.setEnabled(is_custom)

    def redraw_canvas_and_image(self):
        self.graphics_scene.clear()
        theme_colors = get_theme_colors(self.current_theme)

        if self.canvas_width_px > 0 and self.canvas_height_px > 0:
            canvas_color = theme_colors['canvas_fill_color']
            canvas_border = theme_colors['canvas_border_color']

            self.current_canvas_item = self.graphics_scene.addRect(
                0, 0, self.canvas_width_px, self.canvas_height_px,
                QPen(QColor(canvas_border)), QColor(canvas_color)
            )
            self.graphics_scene.setSceneRect(self.current_canvas_item.rect())
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
            self.graphics_view.centerOn(self.current_canvas_item)
        else:
            self.graphics_view.setSceneRect(QRectF())
            self.current_canvas_item = None

        if self.current_display_image_pil and self.canvas_width_px > 0 and self.canvas_height_px > 0:
            qimage = self.pil_to_qimage(self.current_display_image_pil)
            pixmap = QPixmap.fromImage(qimage)

            self.current_image_item = self.graphics_scene.addPixmap(pixmap)
            self.current_image_item.setPos(
                self.image_position_on_canvas_px['x'],
                self.image_position_on_canvas_px['y']
            )
            self.current_image_item.setFlag(QGraphicsItem.ItemIsMovable, True)
            self.current_image_item.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
            
            if self.current_canvas_item:
                combined_rect = self.current_canvas_item.rect().united(
                    self.current_image_item.sceneBoundingRect())
                self.graphics_view.fitInView(combined_rect, Qt.KeepAspectRatio)
                self.graphics_view.centerOn(combined_rect.center())

    def pil_to_qimage(self, pil_image):
        if pil_image.mode == "RGBA":
            data = pil_image.tobytes("raw", "RGBA")
            qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)
        elif pil_image.mode == "RGB":
            data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGB888)
        else:
            pil_image = pil_image.convert("RGB")
            data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGB888)
        return qimage

    def view_mouse_press_event(self, event):
        if event.button() == Qt.LeftButton and self.current_image_item:
            scene_pos = self.graphics_view.mapToScene(event.position().toPoint())
            item_at_pos = self.graphics_scene.itemAt(scene_pos, self.graphics_view.transform())

            if item_at_pos == self.current_image_item:
                self.is_dragging_image = True
                self.drag_start_pos = self.current_image_item.pos() - scene_pos
                self.graphics_view.setDragMode(QGraphicsView.NoDrag)
                event.accept()
            else:
                super(type(self.graphics_view), self.graphics_view).mousePressEvent(event)
        else:
            super(type(self.graphics_view), self.graphics_view).mousePressEvent(event)

    def view_mouse_move_event(self, event):
        if self.is_dragging_image and self.current_image_item:
            new_pos = self.graphics_view.mapToScene(event.position().toPoint()) + self.drag_start_pos
            self.current_image_item.setPos(new_pos)
            event.accept()
        else:
            super(type(self.graphics_view), self.graphics_view).mouseMoveEvent(event)

    def view_mouse_release_event(self, event):
        if event.button() == Qt.LeftButton and self.is_dragging_image:
            self.is_dragging_image = False
            self.image_position_on_canvas_px['x'] = int(self.current_image_item.x())
            self.image_position_on_canvas_px['y'] = int(self.current_image_item.y())
            event.accept()
        else:
            super(type(self.graphics_view), self.graphics_view).mouseReleaseEvent(event)

    def calculate_non_white_pixels(self):
        if not self.current_display_image_pil or not (self.canvas_width_px > 0 and self.canvas_height_px > 0):
            return 0.0

        # Convertir la imagen a escala de grises para el análisis
        gray_image = self.current_display_image_pil.convert("L")
        histogram = gray_image.histogram()
        
        # Contar píxeles no blancos (0-254 en escala de grises, 255 es blanco)
        non_white_pixels_count = sum(histogram[:254])
        
        # Calcular área total del lienzo (en píxeles)
        total_canvas_area = self.canvas_width_px * self.canvas_height_px
        
        if total_canvas_area == 0:
            return 0.0

        # Calcular porcentaje respecto al lienzo completo
        non_white_percentage = (non_white_pixels_count / total_canvas_area) * 100
        
        return non_white_percentage

    def determine_print_type(self, width_cm, height_cm):
        def fits(dimensions, ref_width, ref_height):
            return (dimensions[0] <= ref_width and dimensions[1] <= ref_height)

        short_side = min(width_cm, height_cm)
        long_side = max(width_cm, height_cm)

        cuarto_dims = PRINT_COSTS["cuarto_pliego"]["dimensions_cm"]
        if fits((width_cm, height_cm), cuarto_dims[0], cuarto_dims[1]) or fits((height_cm, width_cm), cuarto_dims[0], cuarto_dims[1]):
            return "cuarto_pliego"

        medio_dims = PRINT_COSTS["medio_pliego"]["dimensions_cm"]
        if fits((width_cm, height_cm), medio_dims[0], medio_dims[1]) or fits((height_cm, width_cm), medio_dims[0], medio_dims[1]):
            return "medio_pliego"

        if short_side <= 74:
            return "pliego"

        if 75 <= short_side <= 92:
            return "extra_90"
        elif 93 <= short_side <= 102:
            return "extra_100"

        return "large_format"

    def calculate_non_white_pixels_and_update_cost(self):
        from utils import calculate_print_cost, PRINT_COSTS, LINE_COSTS, detect_line_type

        if not self.original_image_pil or not self.current_display_image_pil or not (self.canvas_width_px > 0 and self.canvas_height_px > 0):
            self.pixel_result_label.setText("📊 Resultado: N/A")
            self.selected_print_type_label.setText("📄 Tipo de Pliego: N/A")
            self.cost_result_label.setText("💵 Costo Estimado: N/A")
            return

        non_white_percentage = self.calculate_non_white_pixels()
        self.last_calculated_non_white_percentage = non_white_percentage
        self.pixel_result_label.setText(f"📊 Área No Blanca: {non_white_percentage:.2f}%")

        # Determinar tipo de pliego por dimensiones
        width_cm = pixels_to_cm(self.canvas_width_px)
        height_cm = pixels_to_cm(self.canvas_height_px)
        print_type_key = self.determine_print_type(width_cm, height_cm)

        # Si es línea (0% - 9% área no blanca)
        if 0 <= non_white_percentage <= 9 and print_type_key in LINE_COSTS:
            line_type = detect_line_type(self.current_display_image_pil)
            cost = LINE_COSTS[print_type_key][line_type]
            tipo_texto = f"{PRINT_COSTS[print_type_key]['display_name']} línea {line_type}"
            self.selected_print_type_label.setText(f"📄 Tipo de Pliego: {tipo_texto}")
            self.cost_result_label.setText(f"💵 Costo Estimado: ${cost:,.0f}")
            return

        # Si no es línea, usar lógica normal
        largo_cm = max(width_cm, height_cm)
        cost = calculate_print_cost(print_type_key, non_white_percentage, largo_cm)
        self.selected_print_type_label.setText(f"📄 Tipo de Pliego: {PRINT_COSTS[print_type_key]['display_name']}")
        self.cost_result_label.setText(f"💵 Costo Estimado: ${cost:,.0f}")

    def calculate_and_display_cost(self):
        if not hasattr(self, 'cost_result_label') or not hasattr(self, 'selected_print_type_label'):
            return

        canvas_width_cm = pixels_to_cm(self.canvas_width_px)
        canvas_height_cm = pixels_to_cm(self.canvas_height_px)

        if not (canvas_width_cm > 0 and canvas_height_cm > 0) or not self.original_image_pil:
            self.cost_result_label.setText("Costo Estimado: N/A")
            self.selected_print_type_label.setText("Tipo de Pliego: N/A")
            return

        non_white_percentage = self.last_calculated_non_white_percentage
        best_fit_print_type_key = None

        # Lógica de clasificación revisada
        if (canvas_width_cm <= 53 and canvas_height_cm <= 36) or (canvas_width_cm <= 36 and canvas_height_cm <= 53):
            best_fit_print_type_key = "cuarto_pliego"
        elif (canvas_width_cm <= 73 and canvas_height_cm <= 54) or (canvas_width_cm <= 54 and canvas_height_cm <= 73):
            best_fit_print_type_key = "medio_pliego"
        elif (canvas_width_cm <= 73 and canvas_height_cm <= 105) or (canvas_width_cm <= 105 and canvas_height_cm <= 73):
            best_fit_print_type_key = "pliego"
        elif canvas_width_cm <= 90:
            best_fit_print_type_key = "extra_90"
        elif canvas_width_cm <= 100:
            best_fit_print_type_key = "extra_100"
        else:
            best_fit_print_type_key = "large_format"

        if best_fit_print_type_key:
            try:
                cost = calculate_print_cost(
                    best_fit_print_type_key,
                    non_white_percentage,
                    canvas_height_cm
                )
                display_name = PRINT_COSTS[best_fit_print_type_key]['display_name']

                self.selected_print_type_label.setText(f"Tipo de Pliego: {display_name}")
                self.cost_result_label.setText(f"Costo Estimado: ${cost:,.0f}")

            except KeyError as e:
                self.selected_print_type_label.setText("Error: Tipo no definido")
                self.cost_result_label.setText("Costo: Error")
        else:
            self.selected_print_type_label.setText("Tipo: No determinado")
            self.cost_result_label.setText("Costo: N/A")

    def reset_all(self):
        reply = self.show_message_box(
            "Confirmar Reinicio",
            "¿Está seguro que desea reiniciar toda la aplicación? Se borrarán todos los datos.",
            QMessageBox.Question, QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.canvas_width_px = 0
            self.canvas_height_px = 0
            self.original_image_pil = None
            self.current_display_image_pil = None
            self.image_position_on_canvas_px = {'x': 0, 'y': 0}
            self.current_image_mode = "fit_to_canvas"
            self.preview_scale_factor = 1.0
            self.last_calculated_non_white_percentage = 0.0
            self.current_image_rotation_angle = 0

            self.width_entry_cm.clear()
            self.height_entry_cm.clear()
            self.custom_width_entry_cm.clear()
            self.custom_height_entry_cm.clear()

            self.original_image_info_label.setText("Tamaño Real: N/A")
            self.pixel_result_label.setText("Resultado: N/A")
            self.cost_result_label.setText("Costo Estimado: N/A")
            self.selected_print_type_label.setText("Tipo de Pliego: N/A")

            self.radio_fit_to_canvas.setChecked(True)
            self.maintain_aspect_ratio_checkbox.setChecked(True)
            self.toggle_custom_size_entries()

            self._large_canvas_warned = False
            self.graphics_scene.clear()
            self.redraw_canvas_and_image()
            self.show_message_box(
                "Aplicación Reiniciada", 
                "La aplicación ha sido reiniciada a su estado inicial.", 
                QMessageBox.Information
            )

    def print_canvas(self):
        if not self.canvas_width_px > 0 or not self.canvas_height_px > 0:
            self.show_message_box(
                "Lienzo Vacío", 
                "No hay un lienzo creado para imprimir. Por favor, cree uno primero.", 
                QMessageBox.Warning
            )
            return

        printer = QPrinter(QPrinter.HighResolution)
        setup_dialog = QPrintDialog(printer, self)

        if setup_dialog.exec() == QPrintDialog.Accepted:
            preview_dialog = QPrintPreviewDialog(printer, self)
            preview_dialog.paintRequested.connect(self.print_preview_paint_requested)
            preview_dialog.exec()
        else:
            self.show_message_box(
                "Impresión Cancelada", 
                "La operación de impresión ha sido cancelada.", 
                QMessageBox.Information
            )

    def print_preview_paint_requested(self, printer):
        scene = self.graphics_scene
        scene_rect = scene.itemsBoundingRect()

        if scene_rect.isEmpty() and (self.canvas_width_px > 0 and self.canvas_height_px > 0):
            scene_rect = QRectF(0, 0, self.canvas_width_px, self.canvas_height_px)
        elif scene_rect.isEmpty():
            scene_rect = QRectF(0, 0, 100, 100)

        page_rect = printer.pageRect(QPrinter.DevicePixel)
        x_scale = page_rect.width() / scene_rect.width()
        y_scale = page_rect.height() / scene_rect.height()
        scale = min(x_scale, y_scale)

        painter = QPainter(printer)
        painter.scale(scale, scale)

        remaining_width = (page_rect.width() / scale) - scene_rect.width()
        remaining_height = (page_rect.height() / scale) - scene_rect.height()

        painter.translate(remaining_width / 2 - scene_rect.x(), remaining_height / 2 - scene_rect.y())
        scene.render(painter)
        painter.end()
# ---- fin de ui_app.py ----
