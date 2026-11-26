import os
import sys
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMessageBox
from front.modulo_libros import configurar_pagina_libros
from front.modulo_prestamos import configurar_pagina_prestamos
from front.modulo_usuarios import configurar_pagina_usuarios
from src.auth import iniciar_sesion

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_ESTILOS = os.path.join(BASE_DIR, "front", "styles.qss")
RUTA_LOGIN_UI = os.path.join(BASE_DIR, "front", "pantallas", "login.ui")
RUTA_PRINCIPAL_UI = os.path.join(BASE_DIR, "front", "pantallas", "principal.ui")

# Diccionario global para guardar los datos del usuario en sesión:
# {"id": int, "correo": str, "nombre": str, "rol": str}
sesion_actual = {}

ventana_login = None
ventana_principal = None


def cargar_ui(ruta_ui: str):
    archivo = QFile(ruta_ui)
    if not archivo.open(QFile.ReadOnly):
        raise FileNotFoundError(f"No se pudo abrir el archivo UI: {ruta_ui}")
    cargador = QUiLoader()
    widget = cargador.load(archivo)
    archivo.close()
    return widget


def aplicar_estilos(app: QApplication):
    if os.path.exists(RUTA_ESTILOS):
        with open(RUTA_ESTILOS, "r", encoding="utf-8") as archivo_qss:
            app.setStyleSheet(archivo_qss.read())


def configurar_menu_por_rol(ventana, rol: str):
    """
    Oculta los botones del menú lateral según el rol exacto definido en src/ y sql/:
    - 'administrador': acceso total (Libros, Préstamos, Usuarios, Reportes)
    - 'empleado': acceso a Libros, Préstamos y Reportes (se oculta Usuarios)
    - 'lector': acceso a Libros y Préstamos (se ocultan Usuarios y Reportes)
    """
    ventana.btnLibros.setVisible(True)
    ventana.btnPrestamos.setVisible(True)
    ventana.btnUsuarios.setVisible(rol == "administrador")
    ventana.btnReportes.setVisible(rol in ("administrador", "empleado"))


def abrir_ventana_principal():
    global ventana_principal
    ventana_principal = cargar_ui(RUTA_PRINCIPAL_UI)

    nombre = sesion_actual.get("nombre", "")
    rol = sesion_actual.get("rol", "lector")
    ventana_principal.lblUsuarioSesion.setText(f"{nombre}\nRol: {rol}")

    # Configurar visibilidad de botones según el rol
    configurar_menu_por_rol(ventana_principal, rol)

    # Inicializar módulos: Libros, Préstamos y Usuarios
    refrescar_libros = configurar_pagina_libros(ventana_principal, sesion_actual, cargar_ui)
    refrescar_lectores = configurar_pagina_prestamos(
        ventana_principal, sesion_actual, refrescar_libros
    )
    configurar_pagina_usuarios(
        ventana_principal, sesion_actual, cargar_ui, refrescar_lectores
    )

    # Navegación del menú lateral con QStackedWidget
    ventana_principal.btnLibros.clicked.connect(
        lambda: ventana_principal.stackedPaginas.setCurrentIndex(0)
    )
    ventana_principal.btnPrestamos.clicked.connect(
        lambda: ventana_principal.stackedPaginas.setCurrentIndex(1)
    )
    ventana_principal.btnUsuarios.clicked.connect(
        lambda: ventana_principal.stackedPaginas.setCurrentIndex(2)
    )
    ventana_principal.btnReportes.clicked.connect(
        lambda: ventana_principal.stackedPaginas.setCurrentIndex(3)
    )

    # Iniciar siempre en la página de Libros
    ventana_principal.btnLibros.setChecked(True)
    ventana_principal.stackedPaginas.setCurrentIndex(0)

    # Botón para cerrar sesión
    ventana_principal.btnCerrarSesion.clicked.connect(cerrar_sesion)

    ventana_principal.show()


def procesar_login():
    global sesion_actual
    correo = ventana_login.txtCorreo.text()
    contrasenia = ventana_login.txtContrasenia.text()

    resultado = iniciar_sesion(correo, contrasenia)

    if not resultado["ok"]:
        QMessageBox.warning(ventana_login, "Inicio de sesión", resultado["mensaje"])
        return

    # Guardar datos de sesión: id, correo, nombre, rol
    sesion_actual = resultado["datos"]

    ventana_login.close()
    abrir_ventana_principal()


def cerrar_sesion():
    global sesion_actual
    sesion_actual = {}
    if ventana_principal is not None:
        ventana_principal.close()
    mostrar_login()


def mostrar_login():
    global ventana_login
    ventana_login = cargar_ui(RUTA_LOGIN_UI)
    ventana_login.btnIngresar.clicked.connect(procesar_login)
    ventana_login.txtContrasenia.returnPressed.connect(procesar_login)
    ventana_login.txtCorreo.returnPressed.connect(procesar_login)
    ventana_login.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    aplicar_estilos(app)
    mostrar_login()
    sys.exit(app.exec())
