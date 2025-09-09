# pdf_analyzer.py - archivo actualizado para usar compute_image_pixel_stats (NumPy acelerado)
import os
import fitz  # PyMuPDF
from PIL import Image
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QGroupBox, QTextEdit, QComboBox,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QProgressDialog, QApplication
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent
from utils import (
    cm_to_pixels, pixels_to_cm, DEFAULT_DPI, calculate_print_cost,
    PRINT_COSTS, LINE_COSTS, detect_line_type, compute_image_pixel_stats
)
from styles import get_stylesheet, get_theme_colors
from datetime import datetime


class PDFDropButton(QPushButton):
    def __init__(self, text, parent_tab):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.parent_tab = parent_tab

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if os.path.isfile(local_path) and local_path.lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        file_paths_to_load = []
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    if os.path.isfile(local_path) and local_path.lower().endswith('.pdf'):
                        file_paths_to_load.append(local_path)

            if file_paths_to_load:
                self.parent_tab.load_pdfs(file_paths_to_load)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()


class FolderDropButton(QPushButton):
    def __init__(self, text, parent_tab):
        super().__init__(text)
        self.setAcceptDrops(True)
        self.parent_tab = parent_tab

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_path = url.toLocalFile()
                if os.path.isdir(local_path):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    local_path = url.toLocalFile()
                    if os.path.isdir(local_path):
                        self.parent_tab._load_pdfs_from_folder(local_path)
                        event.acceptProposedAction()
                        return
            event.ignore()
        else:
            event.ignore()


class PDFAnalyzerTab(QWidget):
    def __init__(self, initial_theme="light"):
        super().__init__()
        self.current_theme = initial_theme
        self.pdf_documents = []
        self.analysis_results = []
        self.selected_canvas = None
        self.quotes_history = []

        self.init_ui()
        self.apply_stylesheet(self.current_theme)

    def apply_theme(self, theme):
        """Aplica el tema al PDFAnalyzerTab."""
        self.current_theme = theme
        self.setStyleSheet(get_stylesheet(theme))

    def init_ui(self, initial_theme="light"):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # --- Sección de controles superiores ---
        controls_group = QGroupBox("Opciones de Análisis")
        controls_layout = QVBoxLayout()
        controls_group.setLayout(controls_layout)

        # Primera fila de botones
        buttons_row1 = QHBoxLayout()

        self.load_pdf_btn = PDFDropButton("📂 Cargar PDF(s)", self)
        self.load_pdf_btn.setObjectName("load_pdf_btn")
        self.load_pdf_btn.clicked.connect(lambda: self.load_pdfs(None))
        buttons_row1.addWidget(self.load_pdf_btn)

        self.load_folder_btn = FolderDropButton("📁 Cargar Carpeta", self)
        self.load_folder_btn.setObjectName("load_folder_btn")
        self.load_folder_btn.clicked.connect(self.load_folder_dialog)
        buttons_row1.addWidget(self.load_folder_btn)

        controls_layout.addLayout(buttons_row1)

        # Segunda fila de controles
        controls_row2 = QHBoxLayout()

        # Selector de lienzo con etiqueta
        canvas_container = QHBoxLayout()
        canvas_label = QLabel("Tamaño de lienzo:")
        canvas_label.setFixedWidth(120)
        canvas_container.addWidget(canvas_label)

        self.canvas_combo = QComboBox()
        self.canvas_combo.addItem("🟪 Tamaño original", None)
        self.canvas_combo.addItem("🟦 Pliego (100x70 cm)", "pliego")
        self.canvas_combo.addItem("🟨 Medio pliego (50x70 cm)", "medio_pliego")
        self.canvas_combo.addItem("🟥 Cuarto pliego (50x35 cm)", "cuarto_pliego")
        self.canvas_combo.setCurrentIndex(0)
        self.canvas_combo.currentIndexChanged.connect(self.canvas_selected)
        canvas_container.addWidget(self.canvas_combo)

        controls_row2.addLayout(canvas_container)

        actions_container = QHBoxLayout()
        self.analyze_btn = QPushButton("🔍 Analizar PDF(s)")
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.clicked.connect(self.analyze_pdfs)
        self.analyze_btn.setEnabled(False)
        actions_container.addWidget(self.analyze_btn)

        self.reset_btn = QPushButton("🔄 Reiniciar")
        self.reset_btn.setObjectName("reset_btn")
        self.reset_btn.clicked.connect(self.reset_analysis)
        actions_container.addWidget(self.reset_btn)

        controls_row2.addLayout(actions_container)
        controls_layout.addLayout(controls_row2)

        main_layout.addWidget(controls_group)

        # --- Información del PDF ---
        self.pdf_info_group = QGroupBox("Información del PDF")
        self.pdf_info_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pdf_info_layout = QVBoxLayout()

        info_grid = QHBoxLayout()

        left_info = QVBoxLayout()
        self.pdf_name_label = QLabel("📄 Archivo: Ningún PDF cargado")
        left_info.addWidget(self.pdf_name_label)

        self.pdf_pages_label = QLabel("📑 Páginas: 0")
        left_info.addWidget(self.pdf_pages_label)

        right_info = QVBoxLayout()
        self.pdf_dimensions_label = QLabel("📏 Dimensiones: N/A")
        right_info.addWidget(self.pdf_dimensions_label)

        self.pdf_canvas_label = QLabel("🖼️ Lienzo aplicado: Ninguno")
        right_info.addWidget(self.pdf_canvas_label)

        info_grid.addLayout(left_info)
        info_grid.addLayout(right_info)
        self.pdf_info_layout.addLayout(info_grid)
        self.pdf_info_group.setLayout(self.pdf_info_layout)

        main_layout.addWidget(self.pdf_info_group)

        # --- Resultados del análisis ---
        self.results_group = QGroupBox("Resultado del Análisis")
        results_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "PDF", "Página", "Dimensiones",
            "% Área Sólido", "Tipo Pliego", "Costo", "Lienzo"
        ])

        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)

        results_layout.addWidget(self.results_table)

        self.summary_label = QLabel("🟰 Resumen: No hay datos analizados")
        self.summary_label.setFont(QFont("Arial", 10, QFont.Bold))
        results_layout.addWidget(self.summary_label, alignment=Qt.AlignRight)

        self.results_group.setLayout(results_layout)
        main_layout.addWidget(self.results_group)

        # --- Detalles de Análisis (2 columnas) ---
        self.console_group = QGroupBox("Detalles de Análisis")
        console_layout = QHBoxLayout()

        # Columna izquierda: Consola de salida
        console_left = QWidget()
        console_left_layout = QVBoxLayout()
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(100)
        console_left_layout.addWidget(self.console)
        console_left.setLayout(console_left_layout)

        # Columna derecha: Historial de cotizaciones (ahora más ancha)
        console_right = QWidget()
        console_right_layout = QVBoxLayout()

        # Título del historial
        history_label = QLabel("📋 Historial de Cotizaciones")
        history_label.setStyleSheet("font-weight: bold;")
        console_right_layout.addWidget(history_label)

        # Tabla de historial
        self.quotes_table = QTableWidget()
        self.quotes_table.setColumnCount(4)
        self.quotes_table.setHorizontalHeaderLabels(["PDF", "Páginas", "Tipo", "Costo"])
        self.quotes_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.quotes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.quotes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.quotes_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.quotes_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.quotes_table.setAlternatingRowColors(True)
        self.quotes_table.setMaximumHeight(200)
        console_right_layout.addWidget(self.quotes_table)

        # Botones de acción (ahora incluye exportar y refrescar)
        button_layout = QHBoxLayout()

        self.add_quote_btn = QPushButton("➕ Agregar Cotización")
        self.add_quote_btn.setObjectName("addQuoteButton")
        self.add_quote_btn.clicked.connect(self.add_current_to_quotes)
        button_layout.addWidget(self.add_quote_btn)

        self.remove_quote_btn = QPushButton("➖ Eliminar Selección")
        self.remove_quote_btn.setObjectName("removeQuoteButton")
        self.remove_quote_btn.clicked.connect(self.remove_selected_quote)
        button_layout.addWidget(self.remove_quote_btn)

        self.refresh_quotes_btn = QPushButton("🔄 Refrescar")
        self.refresh_quotes_btn.setObjectName("refreshQuoteButton")
        self.refresh_quotes_btn.clicked.connect(self.refresh_quotes)
        button_layout.addWidget(self.refresh_quotes_btn)

        console_right_layout.addLayout(button_layout)

        # Botón de exportar ahora en el historial
        self.export_btn = QPushButton("📄 Exportar Reporte")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        console_right_layout.addWidget(self.export_btn)

        console_right.setLayout(console_right_layout)

        # Ajustamos los tamaños relativos (ahora el historial es más ancho)
        console_layout.addWidget(console_left, 60)  # 60% para la consola
        console_layout.addWidget(console_right, 40)  # 40% para el historial (antes era 30)
        self.console_group.setLayout(console_layout)
        main_layout.addWidget(self.console_group)

        self.setLayout(main_layout)

    def apply_stylesheet(self, theme):
        self.current_theme = theme
        theme_colors = get_theme_colors(theme)

        base_style = f"""
        QWidget {{
            font-family: 'Segoe UI', Arial, sans-serif;
        }}
        
        QGroupBox {{
            background-color: {theme_colors['color_panel']};
            border: 1px solid {theme_colors['color_border']};
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 15px;
            font-weight: bold;
            color: {theme_colors['color_accent']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            font-size: 14px;
        }}
        
        QLabel {{
            color: {theme_colors['color_text_primary']};
            font-size: 14px;
            padding: 2px;
        }}
        
        QTextEdit, QTableWidget {{
            background-color: {theme_colors['color_panel']};
            border: 1px solid {theme_colors['color_border']};
            border-radius: 6px;
            color: {theme_colors['color_text_primary']};
            font-size: 13px;
            selection-background-color: {theme_colors['color_accent']};
            selection-color: white;
        }}
        
        QHeaderView::section {{
            background-color: {theme_colors['color_accent']};
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
            font-size: 13px;
        }}
        
        QTableWidget::item {{
            padding: 6px;
        }}
        """

        button_style = f"""
        QPushButton {{
            background-color: {theme_colors['color_accent']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 15px;
            font-size: 14px;
            min-width: 120px;
        }}
        
        QPushButton:hover {{
            background-color: {theme_colors['color_accent_hover']};
        }}
        
        QPushButton:pressed {{
            background-color: {theme_colors['color_accent_pressed']};
            padding: 9px 15px 7px 15px;
        }}
        
        QPushButton:disabled {{
            background-color: {theme_colors['color_text_secondary']};
            color: {theme_colors['color_panel']};
        }}
        """

        important_button_style = f"""
        #load_pdf_btn, #analyze_btn {{
            background-color: #28a745;
            padding: 8px 20px;
        }}
        
        #load_pdf_btn:hover, #analyze_btn:hover {{
            background-color: #218838;
        }}
        
        #reset_btn {{
            background-color: #dc3545;
            padding: 8px 20px;
        }}
        
        #reset_btn:hover {{
            background-color: #c82333;
        }}
        
        #export_btn {{
            background-color: #17a2b8;
            padding: 8px 20px;
        }}
        
        #export_btn:hover {{
            background-color: #138496;
        }}
        
        /* Estilos para los botones del historial */
        #addQuoteButton {{
            background-color: #28a745;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #addQuoteButton:hover {{
            background-color: #218838;
        }}
        #removeQuoteButton {{
            background-color: #dc3545;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #removeQuoteButton:hover {{
            background-color: #c82333;
        }}
        #refreshQuoteButton {{
            background-color: #ffc107;
            color: #212529;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #refreshQuoteButton:hover {{
            background-color: #e0a800;
        }}
        """

        combo_style = f"""
        QComboBox {{
            background-color: {theme_colors['color_panel']};
            border: 2px solid {theme_colors['color_border']};
            border-radius: 6px;
            padding: 8px;
            min-width: 200px;
            font-size: 14px;
            color: {theme_colors['color_text_primary']};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 25px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {theme_colors['color_panel']};
            border: 2px solid {theme_colors['color_accent']};
            selection-background-color: {theme_colors['color_accent']};
            selection-color: white;
            color: {theme_colors['color_text_primary']};
            padding: 8px;
            font-size: 13px;
            outline: none;
        }}
        
        QComboBox:hover {{
            border: 2px solid {theme_colors['color_accent']};
        }}
        
        QComboBox:focus {{
            border: 2px solid {theme_colors['color_accent']};
        }}
        """

        table_style = """
        QTableWidget {
            gridline-color: #e0e0e0;
        }
        QTableWidget::item {
            border-bottom: 1px solid #e0e0e0;
        }
        """

        if theme == "light":
            table_style += """
            QTableWidget {
                alternate-background-color: #f5f5f5;
            }
            """
        else:
            table_style += """
            QTableWidget {
                alternate-background-color: #2d2d2d;
                gridline-color: #3d3d3d;
            }
            QTableWidget::item {
                border-bottom: 1px solid #3d3d3d;
            }
            """

        self.setStyleSheet(base_style + button_style + important_button_style + combo_style + table_style)

    def refresh_quotes(self):
        """Elimina todas las cotizaciones del historial"""
        reply = QMessageBox.question(
            self, "Confirmar Refresco",
            "¿Está seguro que desea eliminar todas las cotizaciones del historial?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.quotes_table.setRowCount(0)
            self.quotes_history = []
            self.log_message("🔄 Historial de cotizaciones refrescado")

    def add_current_to_quotes(self):
        """Añade la cotización actual al historial"""
        if not self.analysis_results:
            self.log_message("⚠️ No hay resultados para agregar al historial")
            return

        pdf_names = ", ".join(set(result['pdf_name']
                            for result in self.analysis_results))
        total_pages = len(self.analysis_results)
        print_type = self.analysis_results[0]['print_type']
        total_cost = sum(result['cost'] for result in self.analysis_results)

        row_position = self.quotes_table.rowCount()
        self.quotes_table.insertRow(row_position)
        self.quotes_table.setItem(row_position, 0, QTableWidgetItem(pdf_names))
        self.quotes_table.setItem(
            row_position, 1, QTableWidgetItem(str(total_pages)))
        self.quotes_table.setItem(row_position, 2, QTableWidgetItem(print_type))
        cost_item = QTableWidgetItem(f"${total_cost:,.0f}")
        cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.quotes_table.setItem(row_position, 3, cost_item)

        self.quotes_history.append({
            'pdf_names': pdf_names,
            'total_pages': total_pages,
            'print_type': print_type,
            'total_cost': total_cost,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'detailed_results': self.analysis_results.copy()  # ✅ Aquí se agregan los detalles
        })

        self.log_message("✅ Cotización agregada al historial")


    def remove_selected_quote(self):
        """Elimina la cotización seleccionada del historial"""
        selected_row = self.quotes_table.currentRow()
        if selected_row >= 0:
            self.quotes_table.removeRow(selected_row)
            if selected_row < len(self.quotes_history):
                self.quotes_history.pop(selected_row)
            self.log_message("🗑️ Cotización eliminada del historial")
        else:
            self.log_message("⚠️ Seleccione una cotización para eliminar")

    def canvas_selected(self, index):
        self.selected_canvas = self.canvas_combo.itemData(index)
        canvas_name = self.canvas_combo.currentText().split(' ')[0]
        self.pdf_canvas_label.setText(f"🖼️ Lienzo aplicado: {canvas_name.split(' ')[0]}")

        if self.pdf_documents:
            self.update_pdf_info()

    def load_pdfs(self, file_paths=None):
        if file_paths is None:
            file_dialog = QFileDialog(self)
            file_dialog.setNameFilter("Archivos PDF (*.pdf)")
            file_dialog.setFileMode(QFileDialog.ExistingFiles)

            if file_dialog.exec():
                file_paths = file_dialog.selectedFiles()
            else:
                return

        if file_paths:
            self.pdf_documents = []
            loaded_count = 0
            for file_path in file_paths:
                try:
                    doc = fitz.open(file_path)
                    self.pdf_documents.append({
                        'path': file_path,
                        'name': os.path.basename(file_path),
                        'document': doc,
                        'page_count': doc.page_count
                    })
                    loaded_count += 1
                except Exception as e:
                    self.log_message(f"Error al cargar {os.path.basename(file_path)}: {str(e)}")

            if self.pdf_documents:
                self.update_pdf_info()
                self.analyze_btn.setEnabled(True)
                self.log_message(f"{loaded_count} PDF(s) cargado(s) correctamente.")
            else:
                self.log_message("No se cargaron PDFs válidos.")
                self.analyze_btn.setEnabled(False)

    def load_folder_dialog(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if folder_path:
            self._load_pdfs_from_folder(folder_path)

    def _load_pdfs_from_folder(self, folder_path):
        self.pdf_documents = []
        found_pdfs = []
        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith('.pdf'):
                file_path = os.path.join(folder_path, file_name)
                found_pdfs.append(file_path)

        if found_pdfs:
            self.load_pdfs(found_pdfs)
            self.log_message(f"{len(found_pdfs)} PDF(s) cargado(s) desde la carpeta '{os.path.basename(folder_path)}'.")
        else:
            self.log_message(f"No se encontraron PDFs en la carpeta '{os.path.basename(folder_path)}'.")
            if not self.pdf_documents:
                self.analyze_btn.setEnabled(False)


    def update_pdf_info(self):
        if self.pdf_documents:
            total_pages = sum(pdf['page_count'] for pdf in self.pdf_documents)

            # Procesar nombres de archivos para visualización
            displayed_names = []
            full_names = []
            max_files_to_show = 3  # Máximo de archivos a mostrar antes de agregar "y otros X más"
            max_name_length = 20    # Longitud máxima antes de recortar

            for pdf in self.pdf_documents[:max_files_to_show]:
                name = pdf['name']
                full_names.append(name)

                # Recortar nombre si es muy largo
                if len(name) > max_name_length:
                    # Conserva extensión .pdf
                    name = f"{name[:max_name_length-3]}..."

                displayed_names.append(name)

            # Construir cadena para mostrar
            files_display = ", ".join(displayed_names)
            if len(self.pdf_documents) > max_files_to_show:
                files_display += f" y otros {len(self.pdf_documents)-max_files_to_show} más"

            # Actualizar interfaz
            self.pdf_name_label.setText(f"📄 Archivo(s): {files_display}")
            self.pdf_name_label.setToolTip(
                "\n".join(pdf['name'] for pdf in self.pdf_documents))

            self.pdf_pages_label.setText(f"📑 Páginas totales: {total_pages}")
            self.pdf_pages_label.setToolTip(
                "Detalle por archivo:\n" +
                "\n".join(f"• {pdf['name']}: {pdf['page_count']} páginas"
                        for pdf in self.pdf_documents)
            )

            # Manejo de lienzo y dimensiones
            canvas_name = self.canvas_combo.currentText().split(' ')[0]
            self.pdf_canvas_label.setText(f"🖼️ Lienzo aplicado: {canvas_name}")

            # Obtener dimensiones del primer PDF
            first_pdf = self.pdf_documents[0]
            page = first_pdf['document'].load_page(0)
            width_pt = page.rect.width
            height_pt = page.rect.height
            width_cm = round(width_pt * 2.54 / 72, 2)
            height_cm = round(height_pt * 2.54 / 72, 2)

            # Mostrar dimensiones según si hay lienzo seleccionado
            if self.selected_canvas:
                canvas_dims = PRINT_COSTS[self.selected_canvas]["dimensions_cm"]
                dims_text = (f"📏 Dimensiones referencia: {width_cm} cm × {height_cm} cm "
                            f"(Ajustado a: {canvas_dims[0]} cm × {canvas_dims[1]} cm)")
            else:
                dims_text = f"📏 Dimensiones referencia: {width_cm} cm × {height_cm} cm"

            self.pdf_dimensions_label.setText(dims_text)
            self.pdf_dimensions_label.setToolTip(
                f"Dimensiones originales:\n"
                f"Ancho: {width_cm} cm\n"
                f"Alto: {height_cm} cm\n"
                f"Resolución: {DEFAULT_DPI} DPI"
            )

        else:
            # Estado cuando no hay PDFs cargados
            self.pdf_name_label.setText("📄 Archivo: Ningún PDF cargado")
            self.pdf_name_label.setToolTip("")
            self.pdf_pages_label.setText("📑 Páginas: 0")
            self.pdf_pages_label.setToolTip("")
            self.pdf_dimensions_label.setText("📏 Dimensiones: N/A")
            self.pdf_dimensions_label.setToolTip("")
            self.pdf_canvas_label.setText("🖼️ Lienzo aplicado: Ninguno")

    def analyze_pdfs(self):
        if not self.pdf_documents:
            self.log_message("No hay PDFs cargados para analizar.")
            return

        self.progress = QProgressDialog("Analizando archivos PDF...", "Cancelar", 0, 100, self)
        self.progress.setWindowTitle("Procesando")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setAutoClose(True)
        self.progress.setAutoReset(True)
        self.progress.setMinimumDuration(0)

        self.set_ui_enabled(False)

        self.progress.show()
        QApplication.processEvents()

        QTimer.singleShot(100, self.start_analysis)

    def start_analysis(self):
        try:
            self.analysis_results = []
            self.results_table.setRowCount(0)

            total_pages = sum(pdf['page_count'] for pdf in self.pdf_documents)
            processed_pages = 0

            for pdf_idx, pdf in enumerate(self.pdf_documents):
                doc = pdf['document']
                for page_num in range(doc.page_count):
                    if self.progress.wasCanceled():
                        break

                    processed_pages += 1
                    progress = int((processed_pages / total_pages) * 100)
                    self.progress.setValue(progress)
                    self.progress.setLabelText(f"Procesando: {pdf['name']} (página {page_num + 1}/{doc.page_count})")

                    QApplication.processEvents()

                    try:
                        page = doc.load_page(page_num)

                        mat = fitz.Matrix(DEFAULT_DPI / 72.0, DEFAULT_DPI / 72.0)
                        pix = page.get_pixmap(matrix=mat)

                        if pix.alpha:
                            pil_image = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
                        else:
                            pil_image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples).convert("RGBA")

                        width_px = pil_image.width
                        height_px = pil_image.height
                        width_cm_original = pixels_to_cm(max(width_px, height_px))
                        height_cm_original = pixels_to_cm(min(width_px, height_px))

                        if self.selected_canvas:
                            canvas_dims = PRINT_COSTS[self.selected_canvas]["dimensions_cm"]
                            width_cm = max(canvas_dims)
                            height_cm = min(canvas_dims)
                            canvas_name = PRINT_COSTS[self.selected_canvas]["display_name"]
                        else:
                            width_cm = width_cm_original
                            height_cm = height_cm_original
                            canvas_name = "Original"

                        # --- OPTIMIZACIÓN: uso de compute_image_pixel_stats (NumPy) ---
                        try:
                            stats = compute_image_pixel_stats(pil_image)
                            non_white_percentage = int(round(stats.get('non_white_percentage', 0)))
                        except Exception as e:
                            # Fallback al método antiguo si algo falla
                            gray_image = pil_image.convert("L")
                            histogram = gray_image.histogram()
                            non_white_pixels_count = sum(histogram[:254])
                            total_pixels = width_px * height_px
                            non_white_percentage = round((non_white_pixels_count / total_pixels) * 100) if total_pixels > 0 else 0

                        # determinar print_type_key igual que antes
                        if self.selected_canvas:
                            print_type_key = self.selected_canvas
                        else:
                            print_type_key = self.determine_print_type(width_cm_original, height_cm_original)

                        # --- LÓGICA: Si está en 0% - 9% siempre aplicar LINE_COSTS/detect_line_type ---
                        if 0 <= non_white_percentage <= 9 and print_type_key in LINE_COSTS:
                            try:
                                line_type = detect_line_type(pil_image)
                            except Exception as e:
                                # En caso de error, asumimos color para no bajar precio inesperadamente
                                self.log_message(f"Warning detect_line_type failed: {e}")
                                line_type = "color"

                            cost = LINE_COSTS[print_type_key].get(line_type, 0)
                            tipo_texto = f"{PRINT_COSTS.get(print_type_key, {}).get('display_name', print_type_key)} línea {line_type}"

                            # Aplicar redondeos según tipo para mantener consistencia
                            if print_type_key == "cuarto_pliego":
                                cost = round(cost / 500) * 500
                            elif print_type_key in ["pliego", "extra_90", "extra_100", "large_format"]:
                                cost = round(cost / 1000) * 1000

                            result = {
                                'pdf_name': pdf['name'],
                                'page_num': page_num + 1,
                                'dimensions': f"{width_cm:.2f} x {height_cm:.2f} cm",
                                'non_white_percentage': non_white_percentage,
                                'print_type': tipo_texto,
                                'cost': cost,
                                'canvas': canvas_name,
                                'original_dimensions': f"{width_cm_original:.2f} x {height_cm_original:.2f} cm"
                            }
                            self.analysis_results.append(result)
                            self.add_result_row(result)
                            continue
                        # --- FIN LÓGICA LÍNEA ---

                        # Si no es caso "línea", usar la lógica normal
                        cost = calculate_print_cost(print_type_key, non_white_percentage, width_cm)

                        result = {
                            'pdf_name': pdf['name'],
                            'page_num': page_num + 1,
                            'dimensions': f"{width_cm:.2f} x {height_cm:.2f} cm",
                            'non_white_percentage': non_white_percentage,
                            'print_type': PRINT_COSTS[print_type_key]['display_name'],
                            'cost': cost,
                            'canvas': canvas_name,
                            'original_dimensions': f"{width_cm_original:.2f} x {height_cm_original:.2f} cm"
                        }
                        self.analysis_results.append(result)
                        self.add_result_row(result)

                    except Exception as e:
                        self.log_message(f"Error al analizar página {page_num+1} de {pdf['name']}: {str(e)}")

                if self.progress.wasCanceled():
                    break

            if not self.progress.wasCanceled():
                self.progress.setValue(100)
                QApplication.processEvents()

                total_cost = sum(result['cost'] for result in self.analysis_results)
                self.update_summary(total_cost)

                self.export_btn.setEnabled(True)
                self.log_message("✅ Análisis completado.")
            else:
                self.log_message("⚠️ Análisis cancelado por el usuario")

        finally:
            self.set_ui_enabled(True)
            self.progress.close()

    def add_result_row(self, result):
        row_position = self.results_table.rowCount()
        self.results_table.insertRow(row_position)

        self.results_table.setItem(row_position, 0, QTableWidgetItem(result['pdf_name']))
        self.results_table.setItem(row_position, 1, QTableWidgetItem(str(result['page_num'])))
        self.results_table.setItem(row_position, 2, QTableWidgetItem(result['dimensions']))
        self.results_table.setItem(row_position, 3, QTableWidgetItem(f"{result['non_white_percentage']}%"))
        self.results_table.setItem(row_position, 4, QTableWidgetItem(result['print_type']))

        cost_item = QTableWidgetItem(f"${result['cost']:,.0f}")
        cost_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.results_table.setItem(row_position, 5, cost_item)

        self.results_table.setItem(row_position, 6, QTableWidgetItem(result['canvas']))

        self.results_table.scrollToBottom()

    def update_summary(self, total_cost):
        self.summary_label.setText(
            f"🟰 Resumen: {len(self.analysis_results)} páginas analizadas | "
            f"Costo total estimado: ${total_cost:,.0f}"
        )

    def set_ui_enabled(self, enabled):
        self.load_pdf_btn.setEnabled(enabled)
        self.load_folder_btn.setEnabled(enabled)
        self.canvas_combo.setEnabled(enabled)
        self.analyze_btn.setEnabled(enabled and len(self.pdf_documents) > 0)
        self.reset_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled and len(self.analysis_results) > 0)

    def determine_print_type(self, width_cm, height_cm):
        def fits(dimensions, ref_width, ref_height):
            return (dimensions[0] <= ref_width and dimensions[1] <= ref_height)

        short_side = round(min(width_cm, height_cm))
        long_side = round(max(width_cm, height_cm))

        # Primero comprobar cuarto pliego (el más pequeño)
        cuarto_dims = PRINT_COSTS["cuarto_pliego"]["dimensions_cm"]
        if fits((width_cm, height_cm), cuarto_dims[0], cuarto_dims[1]) or fits((height_cm, width_cm), cuarto_dims[0], cuarto_dims[1]):
            return "cuarto_pliego"

        # Luego medio pliego
        medio_dims = PRINT_COSTS["medio_pliego"]["dimensions_cm"]
        if fits((width_cm, height_cm), medio_dims[0], medio_dims[1]) or fits((height_cm, width_cm), medio_dims[0], medio_dims[1]):
            return "medio_pliego"

        # Luego pliego estándar con margen flexible en altura
        if short_side <= 74:
            return "pliego"

        # Finalmente tamaños extra
        if 75 <= short_side <= 92:
            return "extra_90"
        elif 93 <= short_side <= 105:

            return "large_format"


    def export_report(self):
        if not self.quotes_history:
            QMessageBox.warning(
                self, "Advertencia", "No hay cotizaciones en el historial para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Reporte PDF",
            f"Reporte_Cotizaciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            "Archivos PDF (*.pdf)"
        )

        if not file_path:
            return

        try:
            doc = fitz.open()
            # Configuración del documento
            margin = 40
            page_width = 612  # Letter size (8.5 x 11 inches)
            page_height = 792
            content_width = page_width - 2 * margin
            # Configuración de fuentes y colores
            title_font_size = 20
            subtitle_font_size = 16
            section_font_size = 14
            text_font_size = 11
            table_header_font_size = 10
            table_content_font_size = 9
            footer_font_size = 8
            header_color = (0.2, 0.4, 0.6)  # Azul oscuro
            border_color = (0.7, 0.7, 0.7)  # Gris claro
            row_color = (0.95, 0.95, 0.95)  # Gris muy claro
            alternate_row_color = (1, 1, 1)  # Blanco
            accent_color = (0.0, 0.4, 0.7)  # Azul medio

            def add_footer(page_obj, page_number_display):
                footer_text = f"Página {page_number_display}"
                footer_rect = fitz.Rect(
                    margin, page_height - margin + 10,
                    page_width - margin, page_height - margin + 10 + footer_font_size * 1.5
                )
                page_obj.insert_textbox(
                    footer_rect,
                    footer_text,
                    fontname="Helvetica",
                    fontsize=footer_font_size,
                    color=(0.5, 0.5, 0.5),
                    align=fitz.TEXT_ALIGN_CENTER
                )
                page_obj.draw_line(
                    fitz.Point(margin, page_height - margin + 5),
                    fitz.Point(page_width - margin, page_height - margin + 5),
                    color=(0.8, 0.8, 0.8),
                    width=0.5
                )

            page = doc.new_page(width=page_width, height=page_height)
            y_pos = margin

            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "resource", "LOGO_VIRTUA.png")
            if os.path.exists(logo_path):
                logo_rect = fitz.Rect(margin, y_pos, margin + 150, y_pos + 50)
                page.insert_image(logo_rect, filename=logo_path)
                y_pos += 60
            else:
                y_pos += 20

            title_rect = fitz.Rect(margin, y_pos, margin +
                                content_width, y_pos + 30)
            page.insert_textbox(
                title_rect,
                "REPORTE DE COTIZACIONES",
                fontname="Helvetica-Bold",
                fontsize=title_font_size,
                color=(0, 0, 0.5),
                align=fitz.TEXT_ALIGN_CENTER
            )
            y_pos += 40

            date_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            page.insert_text(
                fitz.Point(margin, y_pos),
                f"Generado el: {date_str}",
                fontname="Helvetica",
                fontsize=text_font_size,
                color=(0.5, 0.5, 0.5)
            )
            y_pos += 30

            page.insert_text(
                fitz.Point(margin, y_pos),
                "RESUMEN GENERAL",
                fontname="Helvetica-Bold",
                fontsize=section_font_size,
                color=accent_color
            )
            y_pos += 25

            total_cotizaciones = len(self.quotes_history)
            total_paginas_global = sum(quote['total_pages']
                                    for quote in self.quotes_history)
            total_costo_global = sum(quote['total_cost']
                                    for quote in self.quotes_history)
            summary_lines = [
                f"• Total de cotizaciones registradas: {total_cotizaciones}",
                f"• Total de páginas analizadas en todas las cotizaciones: {total_paginas_global}",
                f"• Costo total estimado global: ${total_costo_global:,.0f}"
            ]

            for line in summary_lines:
                page.insert_text(
                    fitz.Point(margin + 20, y_pos),
                    line,
                    fontname="Helvetica",
                    fontsize=text_font_size,
                    color=(0, 0, 0))
                y_pos += 20

            y_pos += 30
            add_footer(page, 1)  # Footer para la página de resumen

            current_page_number = 1  # Empezamos desde la página 1 (resumen)

            for idx, quote_data in enumerate(self.quotes_history):
                if y_pos > page_height - 200:
                    page = doc.new_page(width=page_width, height=page_height)
                    current_page_number += 1
                    y_pos = margin
                    page.insert_text(
                        fitz.Point(margin, y_pos),
                        "REPORTE DE COTIZACIONES (Continuación)",
                        fontname="Helvetica-Bold",
                        fontsize=subtitle_font_size,
                        color=accent_color
                    )
                    y_pos += 30

                page.insert_text(
                    fitz.Point(margin, y_pos),
                    f"COTIZACIÓN {idx + 1}",
                    fontname="Helvetica-Bold",
                    fontsize=section_font_size,
                    color=accent_color
                )
                y_pos += 25

                quote_summary_lines = [
                    f"Archivo(s): {quote_data['pdf_names']}",
                    f"Páginas totales: {quote_data['total_pages']}",
                    f"Tipo de impresión: {quote_data['print_type']}",
                    f"Costo Total de Cotización: ${quote_data['total_cost']:,.0f}",
                    f"Fecha y Hora: {quote_data['timestamp']}"
                ]

                for line in quote_summary_lines:
                    if y_pos + 20 > page_height - margin:
                        add_footer(page, current_page_number)
                        page = doc.new_page(width=page_width, height=page_height)
                        current_page_number += 1
                        y_pos = margin

                    page.insert_text(
                        fitz.Point(margin + 20, y_pos),
                        line,
                        fontname="Helvetica",
                        fontsize=text_font_size,
                        color=(0, 0, 0)
                    )
                    y_pos += 18

                y_pos += 15

                if 'detailed_results' in quote_data and quote_data['detailed_results']:
                    if y_pos + 40 > page_height - margin:
                        add_footer(page, current_page_number)
                        page = doc.new_page(width=page_width, height=page_height)
                        current_page_number += 1
                        y_pos = margin

                    page.insert_text(
                        fitz.Point(margin, y_pos),
                        "Detalle de Análisis de PDF(s):",
                        fontname="Helvetica-Bold",
                        fontsize=text_font_size + 1,
                        color=(0.2, 0.2, 0.2)
                    )
                    y_pos += 20

                    table_headers = ["PDF", "Pág.", "Dimensiones",
                                    "% Sólido", "Tipo Pliego", "Costo", "Lienzo"]
                    col_widths_analysis = [100, 30, 80, 50, 80, 60, 80]
                    total_table_width = sum(col_widths_analysis)
                    cell_height = 20

                    if y_pos + cell_height > page_height - margin:
                        add_footer(page, current_page_number)
                        page = doc.new_page(width=page_width, height=page_height)
                        current_page_number += 1
                        y_pos = margin

                    x_start_table = margin
                    page.draw_rect(
                        fitz.Rect(x_start_table, y_pos, x_start_table +
                                total_table_width, y_pos + cell_height),
                        color=header_color,
                        fill=header_color,
                        width=1
                    )

                    current_x = x_start_table
                    for i, header in enumerate(table_headers):
                        header_rect = fitz.Rect(
                            current_x, y_pos, current_x + col_widths_analysis[i], y_pos + cell_height)
                        page.insert_textbox(
                            header_rect,
                            header,
                            fontname="Helvetica",
                            fontsize=table_header_font_size,
                            color=(1, 1, 1),
                            align=fitz.TEXT_ALIGN_CENTER
                        )
                        current_x += col_widths_analysis[i]

                    y_pos += cell_height

                    for i, result in enumerate(quote_data['detailed_results']):
                        if y_pos + cell_height > page_height - margin:
                            add_footer(page, current_page_number)
                            page = doc.new_page(width=page_width, height=page_height)
                            current_page_number += 1
                            y_pos = margin
                            x_start_table = margin
                            page.draw_rect(
                                fitz.Rect(x_start_table, y_pos, x_start_table +
                                        total_table_width, y_pos + cell_height),
                                color=header_color,
                                fill=header_color,
                                width=1
                            )
                            current_x = x_start_table
                            for j, header in enumerate(table_headers):
                                header_rect = fitz.Rect(
                                    current_x, y_pos, current_x + col_widths_analysis[j], y_pos + cell_height)
                                page.insert_textbox(
                                    header_rect,
                                    header,
                                    fontname="Helvetica",
                                    fontsize=table_header_font_size,
                                    color=(1, 1, 1),
                                    align=fitz.TEXT_ALIGN_CENTER
                                )
                                current_x += col_widths_analysis[j]
                            y_pos += cell_height

                        fill_color = row_color if i % 2 == 0 else alternate_row_color
                        current_x = x_start_table

                        pdf_name_display = result['pdf_name']
                        if len(pdf_name_display) > 18:
                            pdf_name_display = pdf_name_display[:15] + "..."

                        cells = [
                            pdf_name_display,
                            str(result['page_num']),
                            result['dimensions'],
                            f"{result['non_white_percentage']}%",
                            result['print_type'],
                            f"${result['cost']:,.0f}",
                            result['canvas']
                        ]

                        for j, cell_content in enumerate(cells):
                            cell_rect = fitz.Rect(
                                current_x, y_pos, current_x + col_widths_analysis[j], y_pos + cell_height)
                            page.draw_rect(
                                cell_rect,
                                color=border_color,
                                fill=fill_color,
                                width=0.5
                            )
                            align = fitz.TEXT_ALIGN_LEFT if j == 0 else fitz.TEXT_ALIGN_CENTER
                            if j == 5:  # Columna de costo
                                align = fitz.TEXT_ALIGN_RIGHT
                            page.insert_textbox(
                                cell_rect,
                                cell_content,
                                fontname="Helvetica",
                                fontsize=table_content_font_size,
                                color=(0, 0, 0),
                                align=align
                            )
                            current_x += col_widths_analysis[j]

                        y_pos += cell_height

                    y_pos += 20  # Espacio después de la tabla

                if idx < len(self.quotes_history) - 1 and y_pos + 20 < page_height - margin:
                    page.draw_line(
                        fitz.Point(margin, y_pos),
                        fitz.Point(page_width - margin, y_pos),
                        color=(0.8, 0.8, 0.8),
                        width=1
                    )
                    y_pos += 15

            add_footer(page, current_page_number)

            doc.save(file_path)
            doc.close()
            self.log_message(
                f"✅ Reporte de cotizaciones exportado correctamente a: {file_path}")
            QMessageBox.information(
                self, "Éxito", f"El reporte se ha guardado en:\n{file_path}")

        except Exception as e:
            self.log_message(f"Error al exportar reporte: {str(e)}")
            QMessageBox.critical(
                self, "Error", f"No se pudo exportar el reporte:\n{str(e)}")


    def reset_analysis(self):
        reply = QMessageBox.question(
            self, "Confirmar Reinicio",
            "¿Está seguro que desea reiniciar el análisis? Se perderán todos los datos.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.pdf_documents = []
            self.analysis_results = []
            self.selected_canvas = None
            self.canvas_combo.setCurrentIndex(0)

            self.pdf_name_label.setText("📄 Archivo: Ningún PDF cargado")
            self.pdf_pages_label.setText("📑 Páginas: 0")
            self.pdf_dimensions_label.setText("📏 Dimensiones: N/A")
            self.pdf_canvas_label.setText("🖼️ Lienzo aplicado: Ninguno")
            self.analyze_btn.setEnabled(False)
            self.export_btn.setEnabled(False)

            self.results_table.setRowCount(0)
            self.summary_label.setText("🟰 Resumen: No hay datos analizados")
            self.console.clear()

            self.log_message("🔄 Análisis reiniciado.")

    def log_message(self, message):
        self.console.append(message)
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum())

    def closeEvent(self, event):
        for pdf in self.pdf_documents:
            if 'document' in pdf and pdf['document']:
                pdf['document'].close()
        event.accept()
