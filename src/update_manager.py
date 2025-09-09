# src/update_manager.py
import requests
import os
import sys
import zipfile
import subprocess
import json
# Asegúrate de importar QApplication
from PySide6.QtWidgets import QMessageBox, QApplication

# Define la versión de tu aplicación (se importa desde version.py)
from version import __version__ as APP_VERSION

# --- ¡IMPORTANTE! ---
# Cambia esta URL a donde alojarás el archivo `latest_version.json` en tu servidor.
# Por ahora, puedes dejarla así si no tienes un servidor configurado, pero no funcionará la actualización.
# Ejemplo: "https://tudominio.com/updates/latest_version.json"
UPDATE_INFO_URL = "http://tu_servidor.com/updates/latest_version.json"
# -------------------


def check_for_updates(parent_window):
    try:
        response = requests.get(UPDATE_INFO_URL)
        response.raise_for_status()  # Lanza excepción para errores HTTP
        update_info = response.json()
        latest_version = update_info.get("version")
        download_url = update_info.get("download_url")
        release_notes = update_info.get(
            "release_notes", "No hay notas de la versión disponibles.")

        if not latest_version or not download_url:
            QMessageBox.warning(parent_window, "Error de Actualización",
                                "Información de actualización incompleta en el servidor.")
            return

        # Convertir versiones a tuplas de enteros para una comparación correcta (ej. "1.0.9" < "1.0.10")
        current_version_parts = list(map(int, APP_VERSION.split('.')))
        latest_version_parts = list(map(int, latest_version.split('.')))

        if latest_version_parts > current_version_parts:
            reply = QMessageBox.question(
                parent_window, "Actualización Disponible",
                f"¡Una nueva versión ({latest_version}) está disponible!\n\nNotas de la versión:\n{release_notes}\n\n¿Desea descargar e instalar la actualización ahora?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                download_and_install_update(download_url, parent_window)
        # else: # No es necesario mostrar este mensaje si la app arranca y ya está actualizada
        #     QMessageBox.information(parent_window, "Actualización", "Ya tienes la última versión instalada.")

    except requests.exceptions.RequestException as e:
        QMessageBox.warning(parent_window, "Error de Conexión",
                            f"No se pudo conectar al servidor de actualizaciones: {e}")
    except json.JSONDecodeError:
        QMessageBox.warning(parent_window, "Error de Actualización",
                            "Formato de información de actualización no válido en el servidor.")
    except Exception as e:
        QMessageBox.critical(
            parent_window, "Error", f"Ocurrió un error inesperado al buscar actualizaciones: {e}")


def download_and_install_update(download_url, parent_window):
    # Directorio donde se ejecuta CotizadorApp.exe (o donde están los archivos de la app)
    app_dir = os.path.dirname(sys.executable)
    temp_zip_path = os.path.join(app_dir, "update.zip")
    updater_bat_path = os.path.join(app_dir, "apply_update.bat")

    try:
        # Muestra un mensaje de descarga y procesa eventos para que se vea
        msg_box = QMessageBox(parent_window)
        msg_box.setWindowTitle("Descargando Actualización")
        msg_box.setText("Descargando actualización, por favor espere...")
        msg_box.setStandardButtons(QMessageBox.NoButton)
        msg_box.show()
        QApplication.processEvents()

        response = requests.get(download_url, stream=True)
        response.raise_for_status()  # Lanza excepción para errores HTTP

        with open(temp_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        msg_box.close()  # Cierra el mensaje de descarga

        # Crear el script BAT que aplicará la actualización
        # timeout /t 5: espera 5 segundos para que la app principal se cierre
        # taskkill /IM CotizadorApp.exe /F: fuerza el cierre de la aplicación si está abierta
        # powershell -command "Expand-Archive ...": descomprime el ZIP.
        # Nota: El ZIP debe contener los archivos de la aplicación directamente o dentro de una subcarpeta que coincida con app_dir
        updater_script_content = f"""
        @echo off
        echo Aplicando actualizacion... Por favor espere.
        timeout /t 5 /nobreak > nul
        taskkill /IM CotizadorApp.exe /F > nul 2>&1

        echo Descomprimiendo archivos...
        powershell -command "Expand-Archive -Path '{temp_zip_path}' -DestinationPath '{app_dir}' -Force"

        echo Limpiando archivos temporales...
        del "{temp_zip_path}"
        del "{updater_bat_path}"

        echo Iniciando CotizadorApp...
        start "" "{os.path.join(app_dir, 'CotizadorApp.exe')}"
        exit
        """
        with open(updater_bat_path, "w") as f:
            f.write(updater_script_content)

        QMessageBox.information(parent_window, "Actualización Lista",
                                "La actualización se descargó. La aplicación se reiniciará para aplicar los cambios.")

        # Ejecutar el script BAT y salir de la aplicación actual
        # creationflags=subprocess.DETACHED_PROCESS: el script BAT se ejecuta en un proceso separado
        # para que no se cierre cuando la aplicación principal lo haga.
        subprocess.Popen([updater_bat_path], shell=True,
                         creationflags=subprocess.DETACHED_PROCESS)
        sys.exit()  # Cierra la aplicación actual para que el BAT pueda actualizarla

    except Exception as e:
        QMessageBox.critical(parent_window, "Error de Instalación",
                             f"No se pudo instalar la actualización: {e}")
    finally:
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        # El bat se elimina a sí mismo si se ejecuta correctamente.
        # Solo lo eliminaríamos aquí si el proceso falló antes de que el bat se ejecutara con éxito.
        # if os.path.exists(updater_bat_path):
        #     os.remove(updater_bat_path)
