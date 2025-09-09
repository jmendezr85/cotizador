from PySide6.QtGui import QColor


def get_theme_colors(theme):
    if theme == "light":
        return {
            "color_background": "#F8F9FA",
            "color_panel": "#FFFFFF",
            "color_border": "#DEE2E6",
            "color_text_primary": "#212529",
            "color_text_secondary": "#6C757D",
            "color_accent": "#0D6EFD",
            "color_accent_hover": "#0B5ED7",
            "color_accent_pressed": "#0A58CA",
            "color_error": "#DC3545",
            "color_success": "#28a745",
            "color_info": "#17a2b8",
            "graphics_view_bg": "#E9ECEF",
            "graphics_view_border": "#CED4DA",
            "canvas_border_color": "#212529",
            "canvas_fill_color": "white",
            "table_header_bg": "#0D6EFD",
            "table_header_text": "white",
            "table_row_even": "#FFFFFF",
            "table_row_odd": "#F8F9FA",
            "table_border": "#DEE2E6"
        }
    else:
        return {
            "color_background": "#212529",
            "color_panel": "#343A40",
            "color_border": "#495057",
            "color_text_primary": "#F8F9FA",
            "color_text_secondary": "#CED4DA",
            "color_accent": "#0D6EFD",
            "color_accent_hover": "#0B5ED7",
            "color_accent_pressed": "#0A58CA",
            "color_error": "#DC3545",
            "color_success": "#218838",
            "color_info": "#138496",
            "graphics_view_bg": "#2C3034",
            "graphics_view_border": "#495057",
            "canvas_border_color": "#F8F9FA",
            "canvas_fill_color": "#333333",
            "table_header_bg": "#0B5ED7",
            "table_header_text": "white",
            "table_row_even": "#343A40",
            "table_row_odd": "#2C3034",
            "table_border": "#495057"
        }


def get_stylesheet(theme):
    colors = get_theme_colors(theme)

    base_style = f"""
    * {{
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 14px;
    }}
    
    QMainWindow, QWidget {{
        background-color: {colors['color_background']};
    }}
    
    /* ---- Estilo mejorado para pestañas ---- */
    QTabBar {{
        background: transparent;
        border-bottom: 1px solid {colors['color_border']};
    }}
    
    QTabBar::tab {{
        background: {colors['color_panel']};
        color: {colors['color_text_primary']};
        border: 1px solid {colors['color_border']};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        padding: 8px 16px;
        margin-right: 4px;
        min-width: 120px;
        font-weight: bold;
    }}
    
    QTabBar::tab:selected {{
        background: {colors['color_accent']};
        color: white;
        border-color: {colors['color_accent']};
    }}
    
    QTabBar::tab:hover:!selected {{
        background: {colors['color_accent']}20;
        border-color: {colors['color_accent']};
    }}
    
    QTabWidget::pane {{
        border: 1px solid {colors['color_border']};
        border-top: none;
        border-radius: 0 0 6px 6px;
        margin-top: -1px;
        padding: 10px;
        background: {colors['color_panel']};
    }}
    /* -------------------------------------- */
    
    QGroupBox {{
        background-color: {colors['color_panel']};
        border: 1px solid {colors['color_border']};
        border-radius: 8px;
        margin-top: 10px;
        padding-top: 15px;
        font-weight: bold;
        color: {colors['color_accent']};
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        font-size: 14px;
    }}
    
    QLabel {{
        color: {colors['color_text_primary']};
        font-size: 14px;
        padding: 2px;
    }}
    
    QTextEdit, QTableWidget, QLineEdit {{
        background-color: {colors['color_panel']};
        border: 1px solid {colors['color_border']};
        border-radius: 6px;
        color: {colors['color_text_primary']};
        font-size: 13px;
        selection-background-color: {colors['color_accent']};
        selection-color: white;
    }}
    
    QLineEdit:focus {{
        border: 1px solid {colors['color_accent']};
    }}
    
    QHeaderView::section {{
        background-color: {colors['table_header_bg']};
        color: {colors['table_header_text']};
        padding: 8px;
        border: none;
        font-weight: bold;
        font-size: 13px;
    }}
    
    QTableWidget::item {{
        padding: 6px;
        border-bottom: 1px solid {colors['table_border']};
    }}
    
    QTableWidget {{
        gridline-color: {colors['table_border']};
    }}
    """

    button_style = f"""
    QPushButton {{
        background-color: {colors['color_accent']};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 8px 15px;
        font-size: 14px;
        min-width: 120px;
    }}
    
    QPushButton:hover {{
        background-color: {colors['color_accent_hover']};
    }}
    
    QPushButton:pressed {{
        background-color: {colors['color_accent_pressed']};
        padding: 9px 15px 7px 15px;
    }}
    
    QPushButton:disabled {{
        background-color: {colors['color_text_secondary']};
        color: {colors['color_panel']};
    }}
    """

    important_button_style = f"""
    #load_pdf_btn, #analyze_btn, #load_image_btn, #analyze_pixels_btn {{
        background-color: {colors['color_success']};
        padding: 8px 20px;
    }}
    
    #load_pdf_btn:hover, #analyze_btn:hover, #load_image_btn:hover, #analyze_pixels_btn:hover {{
        background-color: #218838;
    }}
    
    #reset_btn, #ResetButton {{
        background-color: {colors['color_error']};
    }}
    
    #reset_btn:hover, #ResetButton:hover {{
        background-color: #c82333;
    }}
    
    #export_btn, #print_btn {{
        background-color: {colors['color_info']};
        padding: 8px 20px;
    }}
    
    #export_btn:hover, #print_btn:hover {{
        background-color: #138496;
    }}
    
    QPushButton#refreshQuoteButton {{
    background-color: #FFD700; /* Amarillo Oro */
    color: black;
    border: 1px solid {colors['color_border']};
    padding: 5px;
    border-radius: 3px;
}}

QPushButton#refreshQuoteButton:hover {{
    background-color: #FFEE99; /* Un tono más claro de amarillo al pasar el ratón */
}}

QPushButton#removeQuoteButton {{
    background-color: {colors['color_error']}; /* Rojo, usando tu color de error */
    color: white;
    border: 1px solid {colors['color_border']};
    padding: 5px;
    border-radius: 3px;
}}

QPushButton#removeQuoteButton:hover {{
    background-color: #C82333; /* Un rojo un poco más oscuro al pasar el ratón */
}}
"""

    combo_radio_style = f"""
    QComboBox {{
        background-color: {colors['color_panel']};
        border: 2px solid {colors['color_border']};
        border-radius: 6px;
        padding: 8px;
        min-width: 200px;
        font-size: 14px;
        color: {colors['color_text_primary']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 25px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {colors['color_panel']};
        border: 2px solid {colors['color_accent']};
        selection-background-color: {colors['color_accent']};
        selection-color: white;
        color: {colors['color_text_primary']};
        padding: 8px;
        font-size: 13px;
        outline: none;
    }}
    
    QComboBox:hover {{
        border: 2px solid {colors['color_accent']};
    }}
    
    QRadioButton, QCheckBox {{
        color: {colors['color_text_primary']};
        font-size: 14px;
        padding: 5px 0;
        spacing: 8px;
    }}
    
    QRadioButton::indicator, QCheckBox::indicator {{
        width: 18px;
        height: 18px;
    }}
    
    QRadioButton::indicator {{
        border-radius: 9px;
        border: 1px solid {colors['color_border']};
        background-color: {colors['color_background']};
    }}
    
    QRadioButton::indicator:checked {{
        background-color: {colors['color_accent']};
        border-color: {colors['color_accent']};
    }}
    
    QCheckBox::indicator {{
        border-radius: 3px;
        border: 1px solid {colors['color_border']};
        background-color: {colors['color_background']};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {colors['color_accent']};
        border-color: {colors['color_accent']};
    }}
    """

    graphics_style = f"""
    #GraphicsView {{
        border: 1px solid {colors['graphics_view_border']};
        border-radius: 6px;
        background-color: {colors['graphics_view_bg']};
    }}
    """
    footer_style = f"""
/* Estilo para el pie de página */
QWidget#TitleBar {{
    background-color: {colors['color_background']};
    border-bottom: 1px solid {colors['color_border']};
}}

/* Estilo para el botón en el pie de página */
#ThemeToggleButton {{
    background-color: {colors['color_accent']};
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    min-width: 100px;
    margin-right: 10px;
    margin-bottom: 5px;
}}

#ThemeToggleButton:hover {{
    background-color: {colors['color_accent_hover']};
}}
"""

    messagebox_style = f"""
    QMessageBox {{
        background-color: {colors['color_panel']};
        border: 1px solid {colors['color_border']};
        border-radius: 6px;
    }}
    
    QMessageBox QLabel {{
        color: {colors['color_text_primary']};
        font-size: 14px;
    }}
    
    QMessageBox QPushButton {{
        min-width: 80px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    """

    full_style = (base_style + button_style + important_button_style +
                  combo_radio_style + graphics_style + messagebox_style + footer_style)

    return full_style
