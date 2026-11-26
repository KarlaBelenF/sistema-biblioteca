import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QMessageBox, QTableWidgetItem
from src.usuarios import crear_usuario, editar_usuario, listar_usuarios

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_USUARIO_FORM_UI = os.path.join(BASE_DIR, "front", "pantallas", "usuario_form.ui")

ROLES_DISPONIBLES = ["lector", "empleado", "administrador"]


def configurar_pagina_usuarios(
    ventana,
    sesion: dict,
    cargar_ui_fn,
    al_actualizar_usuarios_fn=None,
):
    rol_sesion = sesion.get("rol", "lector")
    id_usuario_sesion = sesion.get("id")
    es_admin = rol_sesion == "administrador"

    # Permisos por rol: Gestión de Usuarios es exclusiva para administrador
    ventana.btnNuevoUsuario.setVisible(es_admin)
    ventana.btnEditarUsuario.setVisible(es_admin)
    ventana.txtBuscarUsuario.setEnabled(es_admin)
    ventana.btnBuscarUsuario.setEnabled(es_admin)
    ventana.btnLimpiarBusquedaUsuario.setEnabled(es_admin)

    if not es_admin:
        ventana.lblEstadoUsuarios.setText(
            "Acceso restringido: solo el administrador puede gestionar usuarios."
        )
        return

    usuarios_actuales = []

    # Configurar columnas de la tabla de usuarios
    header = ventana.tablaUsuarios.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
    header.setSectionResizeMode(1, QHeaderView.Stretch)           # Correo
    header.setSectionResizeMode(2, QHeaderView.Stretch)           # Nombre
    header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Teléfono
    header.setSectionResizeMode(4, QHeaderView.Stretch)           # Dirección
    header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Rol
    header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Estado

    def poblar_tabla(lista_usuarios: list, mensaje_estado: str = ""):
        nonlocal usuarios_actuales
        usuarios_actuales = lista_usuarios or []
        ventana.tablaUsuarios.setRowCount(0)

        for fila_idx, u in enumerate(usuarios_actuales):
            ventana.tablaUsuarios.insertRow(fila_idx)
            estado_texto = "Activo" if bool(u.get("activo")) else "Inactivo"

            valores = [
                str(u["id"]),
                str(u["correo"]),
                str(u["nombre"]),
                str(u["telefono"] if u["telefono"] is not None else ""),
                str(u["direccion"] if u["direccion"] is not None else ""),
                str(u["rol"]),
                estado_texto,
            ]

            for col_idx, texto in enumerate(valores):
                celda = QTableWidgetItem(texto)
                if col_idx in (0, 5, 6):
                    celda.setTextAlignment(Qt.AlignCenter)
                ventana.tablaUsuarios.setItem(fila_idx, col_idx, celda)

        if mensaje_estado:
            ventana.lblEstadoUsuarios.setText(mensaje_estado)

    def cargar_usuarios(filtro: str = ""):
        resultado = listar_usuarios(
            rol=rol_sesion,
            id_usuario=id_usuario_sesion,
            filtro=filtro,
        )
        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Usuarios", resultado["mensaje"])
            return
        poblar_tabla(resultado["datos"], resultado["mensaje"])

    def obtener_usuario_seleccionado():
        fila = ventana.tablaUsuarios.currentRow()
        if fila < 0 or fila >= len(usuarios_actuales):
            return None
        return usuarios_actuales[fila]

    def abrir_formulario_usuario(usuario_editar: dict = None):
        dialogo = cargar_ui_fn(RUTA_USUARIO_FORM_UI)
        dialogo.setParent(ventana, Qt.Dialog)

        for r in ROLES_DISPONIBLES:
            dialogo.cmbRolUsuario.addItem(r, r)

        es_edicion = usuario_editar is not None

        if es_edicion:
            dialogo.setWindowTitle("Editar Usuario")
            dialogo.lblTituloFormulario.setText(
                f"Editar Usuario (ID #{usuario_editar['id']})"
            )
            dialogo.lblContrasenia.setText("Nueva contraseña")
            dialogo.txtContraseniaUsuario.setPlaceholderText(
                "Dejar vacío para conservar la contraseña actual"
            )
            dialogo.txtCorreoUsuario.setText(str(usuario_editar["correo"]))
            dialogo.txtContraseniaUsuario.setText("")
            dialogo.txtNombreUsuario.setText(str(usuario_editar["nombre"]))
            dialogo.txtTelefonoUsuario.setText(
                str(usuario_editar["telefono"] or "")
            )
            dialogo.txtDireccionUsuario.setText(
                str(usuario_editar["direccion"] or "")
            )

            idx_rol = dialogo.cmbRolUsuario.findData(usuario_editar["rol"])
            if idx_rol >= 0:
                dialogo.cmbRolUsuario.setCurrentIndex(idx_rol)

            dialogo.chkActivoUsuario.setChecked(bool(usuario_editar["activo"]))
            dialogo.chkActivoUsuario.setEnabled(True)
        else:
            dialogo.setWindowTitle("Registrar Nuevo Usuario")
            dialogo.lblTituloFormulario.setText("Registrar Nuevo Usuario")
            dialogo.lblContrasenia.setText("Contraseña *")
            dialogo.txtContraseniaUsuario.setPlaceholderText(
                "Ingresa la contraseña"
            )
            dialogo.chkActivoUsuario.setChecked(True)
            dialogo.chkActivoUsuario.setEnabled(False)

        def guardar():
            correo = dialogo.txtCorreoUsuario.text().strip()
            contrasenia = dialogo.txtContraseniaUsuario.text()
            nombre = dialogo.txtNombreUsuario.text().strip()
            telefono = dialogo.txtTelefonoUsuario.text().strip()
            direccion = dialogo.txtDireccionUsuario.text().strip()
            rol_nuevo = dialogo.cmbRolUsuario.currentData()
            activo = dialogo.chkActivoUsuario.isChecked()

            if not telefono or not direccion:
                QMessageBox.warning(
                    dialogo,
                    "Campos requeridos",
                    "Teléfono y dirección son obligatorios.",
                )
                return

            if es_edicion:
                # Si nueva_contrasenia va vacía "", src.usuarios.editar_usuario conserva la actual
                resultado = editar_usuario(
                    rol_sesion=rol_sesion,
                    id_usuario_sesion=id_usuario_sesion,
                    id_objetivo=usuario_editar["id"],
                    correo=correo,
                    nombre=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    rol_nuevo=rol_nuevo,
                    activo=activo,
                    nueva_contrasenia=contrasenia,
                )
            else:
                resultado = crear_usuario(
                    rol_sesion=rol_sesion,
                    id_usuario_sesion=id_usuario_sesion,
                    correo=correo,
                    contrasenia=contrasenia,
                    nombre=nombre,
                    telefono=telefono,
                    direccion=direccion,
                    rol_nuevo=rol_nuevo,
                )

            if not resultado["ok"]:
                QMessageBox.warning(dialogo, "Aviso", resultado["mensaje"])
                return

            QMessageBox.information(dialogo, "Éxito", resultado["mensaje"])
            dialogo.accept()
            cargar_usuarios(ventana.txtBuscarUsuario.text())
            if al_actualizar_usuarios_fn:
                al_actualizar_usuarios_fn()

        dialogo.btnGuardar.clicked.connect(guardar)
        dialogo.btnCancelar.clicked.connect(dialogo.reject)
        dialogo.exec()

    def accion_buscar():
        cargar_usuarios(ventana.txtBuscarUsuario.text())

    def accion_limpiar_busqueda():
        ventana.txtBuscarUsuario.clear()
        cargar_usuarios("")

    def accion_editar():
        usuario = obtener_usuario_seleccionado()
        if not usuario:
            QMessageBox.warning(
                ventana,
                "Selección requerida",
                "Selecciona un usuario de la tabla para editar.",
            )
            return
        abrir_formulario_usuario(usuario_editar=usuario)

    # Conectar eventos
    ventana.btnBuscarUsuario.clicked.connect(accion_buscar)
    ventana.txtBuscarUsuario.returnPressed.connect(accion_buscar)
    ventana.btnLimpiarBusquedaUsuario.clicked.connect(accion_limpiar_busqueda)
    ventana.btnNuevoUsuario.clicked.connect(
        lambda: abrir_formulario_usuario(None)
    )
    ventana.btnEditarUsuario.clicked.connect(accion_editar)

    # Carga inicial de usuarios
    cargar_usuarios("")
