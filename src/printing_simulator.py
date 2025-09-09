# printing_simulator.py
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QGroupBox, QListWidget, QListWidgetItem,
    QMessageBox, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QSizePolicy
)
from PySide6.QtGui import Qt, QBrush, QPen, QColor, QFont, QPainter
from PySide6.QtCore import Qt
from styles import get_stylesheet, get_theme_colors

class PrintingSimulatorTab(QWidget):
    def __init__(self, initial_theme="light"):
        super().__init__()
        self.current_theme = initial_theme
        self.quotes_list = []
        self.counter = 0

        # Valores de materiales
        self.material_prices = {
            'Vinilo': 13600,
            'Lona': 21700,
            'Fotográfico': 13000,
            'Propalcote': 8000,
            'Lienzo': 83000,
            'Pergamino': 6000,
            'Pendón Vertical': 21700,  # Asumiendo el precio de Lona como base para Pendones
            'Pendón Horizontal': 21700  # Asumiendo el precio de Lona como base para Pendones
        }

        # Valores de ploteo
        self.plotting_prices = {
            'general': 25000,
            'general_min': 10000,
            'canvas': 50000,
            'canvas_min': 12500,
            'canvas_material_min': 12500
        }

        # Tubos de aluminio
        self.aluminum_tube_price = 6200

        # Medida mínima
        self.min_measure = 20

        # Inicializar Graphics Scene y View para la previsualización del lienzo
        self.graphics_scene = QGraphicsScene()
        self.graphics_view = QGraphicsView(self.graphics_scene)
        self.graphics_view.setRenderHint(QPainter.Antialiasing)
        self.graphics_view.setAlignment(Qt.AlignCenter)

        self.init_ui()
        self.apply_stylesheet(self.current_theme)

        # Llamada inicial para actualizar la previsualización del encastre al iniciar
        self.update_layout_preview()
        
    def apply_theme(self, theme):
        """Aplica el tema al PrintingSimulatorTab."""
        self.current_theme = theme
        # Si tienes elementos en PrintingSimulatorTab que necesitan actualizar su estilo
        # basándose en el tema, aplícalo aquí.
        self.setStyleSheet(get_stylesheet(theme))
        # Si tienes lógica de dibujo personalizada o widgets que requieren
        # un cambio de color directo, lo harías aquí.
        

    def init_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # --- Columna Izquierda (Contenedor QVBoxLayout para los elementos de la izquierda) ---
        left_column_layout = QVBoxLayout()
        # Espaciado entre grupos en la columna
        left_column_layout.setSpacing(15)

        # Grupo: Calcular Cotización (contiene la creación de la tarjeta y el cálculo)
        form_group = QGroupBox("Calcular Cotización")
        form_layout = QVBoxLayout()
        form_group.setLayout(form_layout)

        # Material selection
        material_layout = QHBoxLayout()
        material_label = QLabel("Material:")
        self.material_combo = QComboBox()
        self.material_combo.addItems(self.material_prices.keys())
        self.material_combo.currentIndexChanged.connect(
            self.validate_material)  # Conectar al validador
        material_layout.addWidget(material_label)
        material_layout.addWidget(self.material_combo)
        form_layout.addLayout(material_layout)

        # Buttons
        buttons_layout = QHBoxLayout()
        self.calculate_btn = QPushButton("💰 Calcular Precio")
        # Originalmente conectado a validate_material
        self.calculate_btn.clicked.connect(self.validate_material)
        buttons_layout.addWidget(self.calculate_btn)

        self.add_quote_btn = QPushButton("➕ Añadir Cotización")
        self.add_quote_btn.clicked.connect(lambda: self.validate_material(
            add_to_list=True))  # Para añadir a la lista
        buttons_layout.addWidget(self.add_quote_btn)

        form_layout.addLayout(buttons_layout)

        # Result display
        self.result_label = QLabel("Precio: -")
        self.result_label.setAlignment(Qt.AlignCenter)
        # Añadir estilo de fuente
        self.result_label.setFont(QFont("Arial", 12, QFont.Bold))
        form_layout.addWidget(self.result_label)

        self.iva_label = QLabel("Los precios no incluyen IVA")
        self.iva_label.setAlignment(Qt.AlignCenter)
        self.iva_label.setVisible(False)
        self.iva_label.setFont(QFont("Arial", 9))  # Añadir estilo de fuente
        form_layout.addWidget(self.iva_label)

        # Añadir a la columna izquierda
        left_column_layout.addWidget(form_group)

        # Grupo: Cotizaciones Añadidas
        quotes_group = QGroupBox("Cotizaciones Realizadas")
        quotes_layout = QVBoxLayout()
        quotes_group.setLayout(quotes_layout)

        self.quotes_list_widget = QListWidget()
        quotes_layout.addWidget(self.quotes_list_widget)

        self.total_label = QLabel("Total: $0 + IVA")
        self.total_label.setAlignment(Qt.AlignRight)
        # Añadir estilo de fuente
        self.total_label.setFont(QFont("Arial", 12, QFont.Bold))
        quotes_layout.addWidget(self.total_label)

        # Botón de limpiar todo, movido aquí para coherencia con la lista
        reset_layout = QHBoxLayout()
        self.reset_btn = QPushButton("🗑️ Borrar Todas")
        self.reset_btn.clicked.connect(self.reset_all)
        reset_layout.addWidget(self.reset_btn)
        quotes_layout.addLayout(reset_layout)

        # Añadir a la columna izquierda
        left_column_layout.addWidget(quotes_group)

        # Añadir la columna izquierda al layout principal QHBoxLayout
        main_layout.addLayout(left_column_layout)

        # --- Columna Derecha (Contenedor QVBoxLayout para los elementos de la derecha) ---
        right_column_layout = QVBoxLayout()
        # Espaciado entre grupos en la columna
        right_column_layout.setSpacing(15)

        # Grupo: Crear Lienzo y Distribuir Piezas
        canvas_preview_group = QGroupBox(
            "Crear Lienzo y Previsualizar Distribución")
        canvas_preview_layout = QVBoxLayout()
        canvas_preview_group.setLayout(canvas_preview_layout)

        # Inputs para dimensiones personalizadas del lienzo
        canvas_dimensions_layout = QHBoxLayout()
        canvas_dimensions_layout.addWidget(QLabel("Ancho Lienzo (cm):"))
        self.canvas_width_input = QLineEdit()
        self.canvas_width_input.setPlaceholderText("Ej. 100")
        self.canvas_width_input.textChanged.connect(
            self.update_layout_preview)  # Conectar a la previsualización
        canvas_dimensions_layout.addWidget(self.canvas_width_input)

        canvas_dimensions_layout.addWidget(QLabel("Alto Lienzo (cm):"))
        self.canvas_height_input = QLineEdit()
        self.canvas_height_input.setPlaceholderText("Ej. 70")
        self.canvas_height_input.textChanged.connect(
            self.update_layout_preview)  # Conectar a la previsualización
        canvas_dimensions_layout.addWidget(self.canvas_height_input)
        canvas_preview_layout.addLayout(canvas_dimensions_layout)

        # Ancho y Alto de Tarjeta/Cuadro
        width_layout = QHBoxLayout()
        width_label = QLabel("Ancho Tarjeta/Cuadro (cm):")
        self.width_input = QLineEdit()
        self.width_input.setPlaceholderText("Ej: 100")
        # También actualiza la previsualización del lienzo
        self.width_input.textChanged.connect(self.update_layout_preview)
        width_layout.addWidget(width_label)
        width_layout.addWidget(self.width_input)
        # Añadido al layout de la derecha
        canvas_preview_layout.addLayout(width_layout)

        # Height input (para la TARJETA/CUADRO)
        height_layout = QHBoxLayout()
        height_label = QLabel("Alto Tarjeta/Cuadro (cm):")
        self.height_input = QLineEdit()
        self.height_input.setPlaceholderText("Ej: 70")
        # También actualiza la previsualización del lienzo
        self.height_input.textChanged.connect(self.update_layout_preview)
        height_layout.addWidget(height_label)
        height_layout.addWidget(self.height_input)
        # Añadido al layout de la derecha
        canvas_preview_layout.addLayout(height_layout)

        # Botón para crear/actualizar el lienzo y previsualizar layout
        self.create_canvas_btn = QPushButton("🎨 Actualizar Previsualización")
        self.create_canvas_btn.clicked.connect(self.update_layout_preview)
        canvas_preview_layout.addWidget(self.create_canvas_btn)

        # Visualización del lienzo y las tarjetas
        canvas_preview_layout.addWidget(self.graphics_view)
        # Establecer la política de tamaño para que el QGraphicsView se expanda
        self.graphics_view.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Etiqueta para mostrar las piezas por lienzo y el desperdicio
        self.layout_info_label = QLabel(
            "Piezas por lienzo: N/A | Desperdicio: N/A")
        self.layout_info_label.setFont(QFont("Arial", 10))
        self.layout_info_label.setAlignment(Qt.AlignCenter)
        canvas_preview_layout.addWidget(self.layout_info_label)

        # Añadir a la columna derecha
        right_column_layout.addWidget(canvas_preview_group)

        # Añadir la columna derecha al layout principal QHBoxLayout
        main_layout.addLayout(right_column_layout)

        # Establecer el QHBoxLayout como layout principal del widget
        self.setLayout(main_layout)

    def validate_material(self, add_to_list=False):
        """Valida las medidas y el material antes de calcular el precio, con opción de añadir a la lista."""
        try:
            material = self.material_combo.currentText()

            # Siempre usar las dimensiones del lienzo para la cotización
            input_width_str = self.canvas_width_input.text()
            input_height_str = self.canvas_height_input.text()

            width = float(input_width_str)
            height = float(input_height_str)

            max_width = self.get_max_width(material)

            # Validar las dimensiones del lienzo con respecto al material seleccionado
            if not self.validate_measures(width, height, max_width, material):
                return

            total_price = 0
            if material == "Lienzo":
                total_price = self.calculate_canvas_price_value(width, height)
            else:
                # Si no es "Lienzo", se usa el precio general, pero con las dimensiones del lienzo
                total_price = self.calculate_general_price_value(
                    width, height, material, max_width)

            self.result_label.setText(f"Precio: ${total_price:,} COP")
            self.iva_label.setVisible(True)

            if add_to_list:
                # Se añaden las cotizaciones siempre con las dimensiones del lienzo
                self.add_quote(material, width, height, total_price)

        except ValueError:
            self.show_message(
                "Error", "Por favor ingrese valores numéricos válidos para las dimensiones del lienzo.", "warning")

    def get_max_width(self, material):
        if material == "Fotográfico":
            return 70
        elif material == "Pergamino":
            return 90
        elif material == "Lienzo":
            return 125
        else:  # Para Vinilo, Lona, Propalcote, Pendón Vertical, Pendón Horizontal
            return 130

    def validate_measures(self, width, height, max_width, material):
        # Los mensajes de advertencia ahora se refieren consistentemente a las dimensiones del lienzo
        dimension_name = "las dimensiones del lienzo"

        # Validación básica de medidas
        if width < self.min_measure or height < self.min_measure:
            self.show_message(
                "Advertencia",
                f"Ambas {dimension_name} deben ser de mínimo {self.min_measure} cm", "warning")
            return False

        # Validaciones especiales para pendones (aplicadas a las dimensiones del lienzo)
        if material == "Pendón Vertical":
            if width > height:
                self.show_message(
                    "Advertencia", "Para este material (Pendón Vertical), el ancho del lienzo no debe ser mayor al alto", "warning")
                return False

        if material == "Pendón Horizontal":
            if height > width:
                self.show_message(
                    "Advertencia", "Para este material (Pendón Horizontal), el alto del lienzo no debe ser mayor al ancho", "warning")
                return False

        # Validación de ancho máximo
        if width > max_width and height > max_width:
            self.show_message(
                "Advertencia", f"Alguna de las dos {dimension_name} debe ser menor o igual a {max_width} para este material", "warning")
            return False

        return True

    def calculate_general_price_value(self, width, height, material, max_width):
        """Calcula el precio para materiales generales y retorna el valor."""
        # Calcular precio del ploteo
        plotting_price = (width / 100) * (height / 100) * \
            self.plotting_prices['general']
        plotting_price = math.ceil(plotting_price / 1000) * 1000
        plotting_price = max(
            plotting_price, self.plotting_prices['general_min'])

        # Calcular precio del material
        material_price = 0
        if width > max_width:
            material_price = (width / 100) * self.material_prices[material]
        elif height > max_width:
            material_price = (height / 100) * self.material_prices[material]
        elif width < height:  # Si el ancho es menor al alto, se usa el ancho para el cálculo base del material
            material_price = (width / 100) * self.material_prices[material]
        else:  # Si el alto es menor o igual al ancho, se usa el alto para el cálculo base del material
            material_price = (height / 100) * self.material_prices[material]

        material_price = math.ceil(material_price / 1000) * 1000

        # Calcular tubos de aluminio para pendones (manteniendo el cálculo original)
        tube_price = 0
        # Estas condiciones se aplican si el material seleccionado es Pendón, y usan las dimensiones del lienzo para el cálculo
        if material in ["Pendón Vertical", "Pendón Horizontal"]:
            # Se asume que el tubo se coloca en el lado que representa el 'ancho' del pendón para la cotización.

            # Si es Pendón Vertical y el ancho del lienzo es menor o igual al alto (orientación vertical del lienzo)
            if material == "Pendón Vertical" and width <= height:
                tube_price = math.ceil(
                    ((width / 100) * self.aluminum_tube_price * 2) / 1000) * 1000
            # Si es Pendón Horizontal y el ancho del lienzo es mayor o igual al alto (orientación horizontal del lienzo)
            elif material == "Pendón Horizontal" and width >= height:
                tube_price = math.ceil(
                    ((width / 100) * self.aluminum_tube_price * 2) / 1000) * 1000
            # Si la orientación del lienzo no coincide con el tipo de pendón seleccionado, no se añaden tubos.
            else:
                tube_price = 0

        total_price = material_price + plotting_price + tube_price
        return total_price

    def calculate_canvas_price_value(self, width, height):
        """Calcula el precio para material Lienzo y retorna el valor."""
        # Calcular precio del ploteo del lienzo
        plotting_price = (width / 100) * (height / 100) * \
            self.plotting_prices['canvas']
        plotting_price = math.ceil(plotting_price / 1000) * 1000
        plotting_price = max(
            plotting_price, self.plotting_prices['canvas_min'])

        # Calcular precio del material del lienzo (con 10cm de margen para encuadre)
        material_price = ((width + 10) / 100) * \
            ((height + 10) / 100) * self.material_prices['Lienzo']
        material_price = math.ceil(material_price / 1000) * 1000
        material_price = max(
            material_price, self.plotting_prices['canvas_material_min'])

        total_price = material_price + plotting_price
        return total_price

    def add_quote(self, material, width, height, price):
        self.counter += 1
        # El texto de la cotización ahora siempre se refiere a las dimensiones del lienzo
        quote_text = f"{material} de {width}cm x {height}cm (Lienzo Cotizado)"

        quote = {
            'id': self.counter,
            'material': material,
            'width': width,  # Estas son las dimensiones del lienzo que se usaron para la cotización
            'height': height,  # Idem
            'price': price,
            'display_text': quote_text  # Guardar el texto formateado para la lista
        }
        self.quotes_list.append(quote)
        self.update_quotes_list()

    def update_quotes_list(self):
        self.quotes_list_widget.clear()
        total = 0

        for quote in self.quotes_list:
            item = QListWidgetItem()
            item.setText(
                f"{quote['id']}: {quote['display_text']} - "
                f"Precio: ${quote['price']:,}"
            )
            self.quotes_list_widget.addItem(item)
            total += quote['price']

        self.total_label.setText(f"Total: ${total:,} + IVA")

    def reset_all(self):
        reply = QMessageBox.question(
            self, 'Confirmar',
            '¿Estás seguro de borrar todas las cotizaciones?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.quotes_list = []
            self.counter = 0
            self.width_input.clear()
            self.height_input.clear()
            self.canvas_width_input.clear()
            self.canvas_height_input.clear()
            self.result_label.setText("Precio: -")
            self.iva_label.setVisible(False)
            self.quotes_list_widget.clear()
            self.total_label.setText("Total: $0 + IVA")
            self.update_layout_preview()  # Limpiar/reiniciar la previsualización gráfica

    def show_message(self, title, message, icon_type="info"):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)

        if icon_type == "warning":
            msg.setIcon(QMessageBox.Warning)
        else:
            msg.setIcon(QMessageBox.Information)

        msg.exec()

    def apply_stylesheet(self, theme):
        """Aplica los estilos visuales según el tema seleccionado"""
        self.current_theme = theme
        # Estilos generales para el tema (adaptados del ejemplo)
        bg_color = "#FFFFFF" if theme == "light" else "#212529"
        text_color = "#212529" if theme == "light" else "#F8F9FA"
        panel_color = "#F0F0F0" if theme == "light" else "#333333"
        border_color = "#DDDDDD" if theme == "light" else "#555555"
        accent_color = "#0D6EFD"

        self.setStyleSheet(f"""
            QWidget {{
                font-family: 'Segoe UI', Arial, sans-serif;
                background-color: {bg_color};
                color: {text_color};
            }}
            QGroupBox {{
                background-color: {panel_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: bold;
                color: {accent_color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                font-size: 14px;
            }}
            QLabel {{
                color: {text_color};
                font-size: 14px;
                padding: 2px;
            }}
            QLineEdit {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px;
                color: {text_color};
            }}
            QComboBox {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 5px;
                color: {text_color};
            }}
            QPushButton {{
                background-color: {accent_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #0B5ED7;
            }}
            QPushButton:pressed {{
                background-color: #0A58CA;
            }}
            QListWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                color: {text_color};
            }}
        """)
        # Estilo específico para la vista gráfica
        self.graphics_view.setStyleSheet(f"""
            QGraphicsView {{
                border: 1px solid {border_color};
                border-radius: 6px;
                background-color: {bg_color};
            }}
        """)

    def update_layout_preview(self):
        """
        Calcula cuántas piezas (tarjetas/cuadros) caben en el lienzo personalizado y dibuja una previsualización.
        """
        self.graphics_scene.clear()

        # Inicializar variables para evitar UnboundLocalError
        count_normal_w = 0
        count_normal_h = 0
        count_rotated_w = 0
        count_rotated_h = 0
        pieces_normal = 0
        pieces_rotated = 0
        item_w_cm = 0  # Inicializar también para que siempre tengan un valor
        item_h_cm = 0  # Inicializar también para que siempre tengan un valor

        # Obtener dimensiones de la pieza (tarjeta/cuadro)
        width_str = self.width_input.text()
        height_str = self.height_input.text()

        try:
            item_w_cm = float(width_str)
            item_h_cm = float(height_str)
            if item_w_cm <= 0 or item_h_cm <= 0:
                self.layout_info_label.setText(
                    "Piezas por lienzo: N/A | Desperdicio: N/A")
                # Dibujar solo el lienzo vacío si las dimensiones de la pieza son inválidas
                # No necesitamos 'pass' aquí, simplemente el control de flujo continuará
            # Ensure graphics view updates even if no pieces fit
        except ValueError:
            self.layout_info_label.setText(
                "Piezas por lienzo: N/A | Desperdicio: N/A")
            item_w_cm = 0  # Set to 0 to prevent drawing items
            item_h_cm = 0  # Set to 0 to prevent drawing items

        # Obtener dimensiones del lienzo personalizado
        canvas_width_str = self.canvas_width_input.text()
        canvas_height_str = self.canvas_height_input.text()

        try:
            sheet_w_cm = float(canvas_width_str)
            sheet_h_cm = float(canvas_height_str)
            if sheet_w_cm <= 0 or sheet_h_cm <= 0:
                self.layout_info_label.setText(
                    "Piezas por lienzo: 0 | Desperdicio: N/A")
                # Still draw empty canvas if canvas dimensions are valid but zero/negative

        except ValueError:
            self.layout_info_label.setText(
                "Piezas por lienzo: N/A | Desperdicio: N/A")
            # Clear graphics scene if canvas dimensions are invalid
            self.graphics_scene.clear()
            return  # Si las dimensiones del lienzo no son válidas, salimos de la función

        # Determine how many items fit in normal orientation (item width along sheet width)
        if item_w_cm > 0 and item_h_cm > 0:  # Only calculate if item dimensions are valid
            count_normal_w = math.floor(sheet_w_cm / item_w_cm)
            count_normal_h = math.floor(sheet_h_cm / item_h_cm)
            pieces_normal = count_normal_w * count_normal_h

        # Determine how many items fit if item is rotated 90 degrees (item height along sheet width)
        if item_w_cm > 0 and item_h_cm > 0:  # Only calculate if item dimensions are valid
            count_rotated_w = math.floor(sheet_w_cm / item_h_cm)
            count_rotated_h = math.floor(sheet_h_cm / item_w_cm)
            pieces_rotated = count_rotated_w * count_rotated_h

        # Elegir la orientación que permita más piezas
        if pieces_normal >= pieces_rotated:
            pieces_per_sheet = pieces_normal
            final_item_w = item_w_cm
            final_item_h = item_h_cm
            num_across = count_normal_w
            num_down = count_normal_h
        else:
            pieces_per_sheet = pieces_rotated
            # Intercambiado para el dibujo (el alto original de la pieza se convierte en su "ancho" en el lienzo)
            final_item_w = item_h_cm
            # Intercambiado para el dibujo (el ancho original de la pieza se convierte en su "alto" en el lienzo)
            final_item_h = item_w_cm
            num_across = count_rotated_w
            num_down = count_rotated_h

        # Calculate wasted area
        sheet_area = sheet_w_cm * sheet_h_cm
        # Usar dimensiones originales de la pieza para el cálculo de área
        items_area = pieces_per_sheet * item_w_cm * item_h_cm

        waste_percent = 0.0
        if sheet_area > 0:
            waste_percent = ((sheet_area - items_area) / sheet_area) * 100

        self.layout_info_label.setText(
            f"Piezas por lienzo: {pieces_per_sheet} | Desperdicio: {waste_percent:.2f}%"
        )

        # Dibujar la previsualización
        # Definir un factor de escala para el dibujo (ej. 5 píxeles por cm)
        PX_PER_CM = 5
        scene_width_px = sheet_w_cm * PX_PER_CM
        scene_height_px = sheet_h_cm * PX_PER_CM

        # Establecer el rectángulo de la escena basado en las dimensiones reales del lienzo
        self.graphics_scene.setSceneRect(0, 0, scene_width_px, scene_height_px)

        # Dibujar el rectángulo del lienzo
        sheet_rect = QGraphicsRectItem(0, 0, scene_width_px, scene_height_px)
        sheet_rect.setPen(QPen(QColor(Qt.black), 2))
        # Color de fondo del lienzo para mayor contraste
        # Un gris medio para el lienzo
        sheet_rect.setBrush(QBrush(QColor("#C0C0C0")))
        self.graphics_scene.addItem(sheet_rect)

        # Dibujar las piezas solo si caben algunas y sus dimensiones son válidas
        if pieces_per_sheet > 0 and item_w_cm > 0 and item_h_cm > 0:
            item_pixel_w = final_item_w * PX_PER_CM
            item_pixel_h = final_item_h * PX_PER_CM

            # CAMBIO: Borde rojo y sin relleno para las piezas
            # Borde rojo más grueso para mayor visibilidad
            item_pen = QPen(QColor(Qt.red), 2)
            item_brush = Qt.NoBrush  # Sin relleno

            current_x = 0
            current_y = 0

            # Dibujar piezas fila por fila
            for row in range(num_down):
                for col in range(num_across):
                    item_rect = QGraphicsRectItem(
                        current_x, current_y, item_pixel_w, item_pixel_h)
                    item_rect.setPen(item_pen)
                    item_rect.setBrush(item_brush)
                    self.graphics_scene.addItem(item_rect)
                    current_x += item_pixel_w
                current_x = 0  # Reiniciar x para la siguiente fila
                current_y += item_pixel_h  # Mover a la siguiente fila

        # Ajustar la vista a la escena
        self.graphics_view.fitInView(
            self.graphics_scene.sceneRect(), Qt.KeepAspectRatio)
