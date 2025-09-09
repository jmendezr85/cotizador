# install.py - Versión sin winshell
import os
import sys
import subprocess
import platform
from pathlib import Path


def check_python_version():
    """Verifica que Python 3.7+ esté instalado"""
    if sys.version_info < (3, 7):
        print("❌ Se requiere Python 3.7 o superior")
        sys.exit(1)
    elif sys.version_info >= (3, 13):
        print("⚠️  Advertencia: Python 3.13 puede tener problemas con algunas dependencias")
        print("   Recomendado usar Python 3.10 o 3.11 para mejor compatibilidad")


def install_dependencies():
    """Instala todas las dependencias del proyecto"""
    print("\n🔍 Instalando dependencias...")

    dependencies = [
        'PySide6>=6.4.0',
        'Pillow>=9.0.0',
        'PyMuPDF>=1.22.0',
        'requests>=2.28.0'
    ]

    for package in dependencies:
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '--upgrade', package])
            print(f"✅ {package.split('>=')[0]} instalado correctamente")
        except subprocess.CalledProcessError:
            print(f"❌ Error al instalar {package}")
            sys.exit(1)


def create_resource_folder():
    """Crea la carpeta resource si no existe"""
    resource_path = os.path.join(os.path.dirname(__file__), 'resource')
    if not os.path.exists(resource_path):
        os.makedirs(resource_path)
        print("\n📁 Carpeta 'resource' creada")
        print("   → Por favor coloca aquí tus archivos de logo (logo.ico, banner_cotizador.png)")


def create_bat_launcher():
    """Crea un archivo .bat para lanzar la aplicación en Windows"""
    if platform.system() == "Windows":
        bat_content = f"""@echo off
"{sys.executable}" "{os.path.join(os.path.dirname(__file__), 'main.py')}"
pause
"""
        bat_path = os.path.join(os.path.dirname(__file__), 'LaunchApp.bat')
        with open(bat_path, 'w') as f:
            f.write(bat_content)
        print(f"\n📝 Archivo batch creado: {bat_path}")
        print("   Doble clic en este archivo para ejecutar la aplicación")


def post_installation_check():
    """Verifica que todo esté correctamente instalado"""
    print("\n🔍 Verificando instalación...")
    check_files = [
        'main.py',
        'utils.py',
        'pdf_analyzer.py',
        os.path.join('resource', 'logo.ico')
    ]

    all_ok = True
    for file in check_files:
        if not os.path.exists(file):
            print(f"⚠️ Archivo faltante: {file}")
            all_ok = False

    if all_ok:
        print("✅ Todos los componentes están listos")
    else:
        print("\n⚠️ Algunos archivos no se encontraron")
        print("   → Asegúrate de tener todos los archivos del proyecto")


def main():
    print("\n" + "="*50)
    print("   INSTALADOR DE COTIZADORAPP v1.0.0")
    print("="*50 + "\n")

    check_python_version()
    install_dependencies()
    create_resource_folder()
    create_bat_launcher()
    post_installation_check()

    print("\n🎉 Instalación completada con éxito!")
    print(f"\nPara ejecutar la aplicación:")
    print(
        f"  1. Navega a esta carpeta: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"  2. Ejecuta: LaunchApp.bat (en Windows)")
    print(f"     o manualmente: {sys.executable} main.py")


if __name__ == "__main__":
    main()
