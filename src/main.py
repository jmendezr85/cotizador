import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget,
                               QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QGraphicsOpacityEffect, QSplashScreen, QLabel, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QSettings, QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PySide6.QtGui import QIcon, QPixmap, QTransform, QGuiApplication
from ui_app import ImageCanvasApp
from pdf_analyzer import PDFAnalyzerTab
from printing_simulator import PrintingSimulatorTab
from styles import get_stylesheet

# --- INICIO: Configuración de High-DPI ---
# Esto debe estar antes de crear QApplication
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1.0"  # Valor inicial, se ajustará automáticamente
QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
# --- FIN: Configuración de High-DPI ---

def resource_path(relative_path):
    """Obtiene la ruta absoluta al recurso, funciona para desarrollo y para PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir))
    return os.path.join(base_path, "resource", relative_path)

def check_for_updates(parent_window):
    QMessageBox.information(
        parent_window,
        "Buscar Actualizaciones",
        "Por favor, selecciona el archivo del nuevo instalador de CotizadorApp (.exe) en tu computadora."
    )

    file_dialog = QFileDialog(parent_window)
    file_dialog.setWindowTitle("Seleccionar Nuevo Instalador")
    file_dialog.setNameFilter("Instaladores (*.exe)")
    file_dialog.setFileMode(QFileDialog.ExistingFile)

    if file_dialog.exec():
        selected_files = file_dialog.selectedFiles()
        if selected_files:
            installer_path = selected_files[0]
            reply = QMessageBox.question(
                parent_window,
                "Confirmar Actualización",
                f"¿Deseas ejecutar este instalador para actualizar CotizadorApp?\n\n{installer_path}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                QMessageBox.information(
                    parent_window,
                    "Actualizando...",
                    "Se cerrará la aplicación para iniciar el proceso de actualización. Por favor, sigue las instrucciones del instalador."
                )
                QApplication.quit()
                os.startfile(installer_path)
            else:
                QMessageBox.information(
                    parent_window,
                    "Actualización Cancelada",
                    "El proceso de actualización ha sido cancelado."
                )
    else:
        QMessageBox.information(
            parent_window,
            "Actualización Cancelada",
            "No se seleccionó ningún archivo de instalador."
        )

class AnimationManager:
    @staticmethod
    def fade_in(widget, duration=400):
        if isinstance(widget, QWidget) and widget.graphicsEffect():
            widget.graphicsEffect().setOpacity(1)

        if isinstance(widget, QMainWindow):
            animation = QPropertyAnimation(widget, b"windowOpacity")
            animation.setDuration(duration)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.setEasingCurve(QEasingCurve.InOutQuad)
            animation.start()
            return animation
        elif isinstance(widget, QWidget):
            opacity_effect = widget.graphicsEffect()
            if not isinstance(opacity_effect, QGraphicsOpacityEffect):
                opacity_effect = QGraphicsOpacityEffect(widget)
                widget.setGraphicsEffect(opacity_effect)

            animation = QPropertyAnimation(opacity_effect, b"opacity")
            animation.setDuration(duration)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.setEasingCurve(QEasingCurve.InOutQuad)
            animation.start()
            return animation
        return None

class MainWindow(QMainWindow):
    def __init__(self, initial_theme="light"):
        super().__init__()
        self.setWindowTitle(f"CotizadorApp v1.0.0")
        
        # Configura el tamaño inicial basado en la pantalla disponible
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setGeometry(
            int(screen_geometry.width() * 0.05),  # 5% del ancho
            int(screen_geometry.height() * 0.05), # 5% del alto
            int(screen_geometry.width() * 0.9),   # 90% del ancho
            int(screen_geometry.height() * 0.9)   # 90% del alto
        )

        self.settings = QSettings("MiEmpresa", "CotizadorApp")
        self.current_theme = self.settings.value("theme", "light", type=str)

        self.image_canvas_tab = ImageCanvasApp(self.current_theme)
        self.pdf_analyzer_tab = PDFAnalyzerTab(self.current_theme)
        self.printing_simulator_tab = PrintingSimulatorTab(self.current_theme)

        self.apply_theme(self.current_theme)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)  # Márgenes uniformes

        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        self.tab_widget.addTab(self.image_canvas_tab, "Lienzo de Imagen")
        self.tab_widget.addTab(self.pdf_analyzer_tab, "Analizador de PDF")
        self.tab_widget.addTab(self.printing_simulator_tab, "Simulador de Impresión")

        # Footer
        self.footer_widget = QWidget()
        self.footer_widget.setObjectName("TitleBar")
        self.footer_layout = QHBoxLayout(self.footer_widget)
        self.footer_layout.setContentsMargins(10, 5, 10, 5)
        self.footer_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.theme_toggle_button = QPushButton("Cambiar Tema")
        self.theme_toggle_button.setObjectName("ThemeToggleButton")
        self.theme_toggle_button.clicked.connect(self.toggle_theme)
        self.footer_layout.addWidget(self.theme_toggle_button)

        self.update_button = QPushButton("Buscar Actualizaciones")
        self.update_button.setObjectName("ThemeToggleButton")
        self.update_button.clicked.connect(lambda: check_for_updates(self))
        self.footer_layout.addWidget(self.update_button)

        self.main_layout.addWidget(self.footer_widget)

    def apply_theme(self, theme):
        self.current_theme = theme
        self.setStyleSheet(get_stylesheet(theme))
        self.image_canvas_tab.apply_theme(theme)
        self.pdf_analyzer_tab.apply_theme(theme)
        self.printing_simulator_tab.apply_theme(theme)
        self.settings.setValue("theme", theme)

    def toggle_theme(self):
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(new_theme)

def main():
    # Configuración de High-DPI ya está arriba (al inicio del archivo)
    app = QApplication(sys.argv)

    app_icon_path = resource_path("logo.ico")
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        print(f"Advertencia: No se encontró el icono de la aplicación en {app_icon_path}.")

    splash_file_name = "banner_cotizador.png"
    splash_path = resource_path(splash_file_name)

    splash = None
    if os.path.exists(splash_path):
        splash_pixmap = QPixmap(splash_path)
        screen = app.primaryScreen()
        scaled_pixmap = splash_pixmap.scaled(
            screen.size() * 0.7,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        splash = QSplashScreen(scaled_pixmap)
        splash.show()
    else:
        print(f"Advertencia: No se encontró el archivo del splash screen en {splash_path}.")
        splash = None

    window = MainWindow()

    def finish_splash():
        if splash:
            splash.finish(window)
        window.showMaximized()  # Cambiado a showMaximized para mejor experiencia
        window._main_window_animation = AnimationManager.fade_in(window, duration=400)

    QTimer.singleShot(3000, finish_splash)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()