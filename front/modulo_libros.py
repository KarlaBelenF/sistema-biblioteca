import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QWidget,
)
from src.libros import (
    buscar_libro_por_codigo,
    editar_libro,
    eliminar_libro,
    escanear_alta_libro,
    listar_libros,
    listar_ubicaciones,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_LIBRO_FORM_UI = os.path.join(BASE_DIR, "front", "pantallas", "libro_form.ui")
RUTA_SINOPSIS_UI = os.path.join(BASE_DIR, "front", "pantallas", "sinopsis_dialog.ui")


def configurar_pagina_libros(ventana, sesion: dict, cargar_ui_fn):
    rol = sesion.get("rol", "lector")
    id_usuario = sesion.get("id")

    # Lista en memoria con los diccionarios actuales mostrados en la tabla
    libros_actuales = []

    # Configurar aspecto de las columnas de la tabla
    header = ventana.tablaLibros.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
    header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Código
    header.setSectionResizeMode(2, QHeaderView.Stretch)           # Título
    header.setSectionResizeMode(3, QHeaderView.Stretch)           # Autor
    header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Edición
    header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Año
    header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Ubicación
    header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Stock
    header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Sinopsis (botón Ver)

    # Ajustar permisos visuales en la página de Libros según el rol
    es_admin = rol == "administrador"
    es_personal = rol in ("administrador", "empleado")

    ventana.btnNuevoLibro.setVisible(es_personal)
    ventana.btnEditarLibro.setVisible(es_personal)
    ventana.btnEliminarLibro.setVisible(es_admin)

    if not es_personal:
        ventana.txtCodigoBarras.setPlaceholderText(
            "Escanee o escriba un código de barras y presione Enter para buscar el libro..."
        )
        ventana.btnEscanearLibro.setText("Buscar código")

    def mostrar_sinopsis(libro: dict):
        dialogo = cargar_ui_fn(RUTA_SINOPSIS_UI)
        dialogo.setParent(ventana, Qt.Dialog)
        dialogo.lblLibroSinopsis.setText(f"{libro['titulo']} — {libro['autor']}")
        sinopsis_texto = (libro.get("sinopsis") or "").strip()
        if not sinopsis_texto:
            sinopsis_texto = "Este libro no tiene una sinopsis registrada."
        dialogo.txtDetalleSinopsis.setPlainText(sinopsis_texto)
        dialogo.btnCerrarSinopsis.clicked.connect(dialogo.accept)
        dialogo.exec()

    def poblar_tabla(lista_libros: list, mensaje_estado: str = ""):
        nonlocal libros_actuales
        libros_actuales = lista_libros or []
        ventana.tablaLibros.setRowCount(0)

        for fila_idx, libro in enumerate(libros_actuales):
            ventana.tablaLibros.insertRow(fila_idx)
            ventana.tablaLibros.setRowHeight(fila_idx, 38)

            ubicacion_texto = f"Estante {libro['estante']} - Fila {libro['fila']}"
            valores = [
                str(libro["id"]),
                str(libro["codigo"]),
                str(libro["titulo"]),
                str(libro["autor"]),
                str(libro["edicion"] if libro["edicion"] is not None else ""),
                str(libro["anio"] if libro["anio"] is not None else ""),
                ubicacion_texto,
                str(libro["stock"]),
            ]

            for col_idx, texto in enumerate(valores):
                item = QTableWidgetItem(texto)
                if col_idx in (0, 4, 5, 7):
                    item.setTextAlignment(Qt.AlignCenter)
                ventana.tablaLibros.setItem(fila_idx, col_idx, item)

            # Botón "Ver" en la columna Sinopsis (columna 8)
            contenedor_btn = QWidget()
            contenedor_btn.setObjectName("celdaBotonTabla")
            layout_btn = QHBoxLayout(contenedor_btn)
            layout_btn.setContentsMargins(6, 4, 6, 4)
            layout_btn.setAlignment(Qt.AlignCenter)

            btn_ver = QPushButton("Ver")
            btn_ver.setObjectName("btnVerSinopsis")
            btn_ver.setCursor(Qt.PointingHandCursor)
            btn_ver.setFixedSize(64, 28)
            btn_ver.clicked.connect(
                lambda _checked=False, lib=libro: mostrar_sinopsis(lib)
            )
            layout_btn.addWidget(btn_ver)
            ventana.tablaLibros.setCellWidget(fila_idx, 8, contenedor_btn)

        if mensaje_estado:
            ventana.lblEstadoLibros.setText(mensaje_estado)

    def cargar_libros(filtro: str = ""):
        resultado = listar_libros(rol, id_usuario, filtro)
        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Libros", resultado["mensaje"])
            return
        poblar_tabla(resultado["datos"], resultado["mensaje"])

    def seleccionar_libro_en_tabla_por_codigo(codigo_buscado: str):
        codigo_buscado = codigo_buscado.strip()
        for fila_idx, libro in enumerate(libros_actuales):
            if str(libro.get("codigo", "")).strip() == codigo_buscado:
                ventana.tablaLibros.selectRow(fila_idx)
                ventana.tablaLibros.scrollToItem(
                    ventana.tablaLibros.item(fila_idx, 0)
                )
                break

    def obtener_libro_seleccionado():
        fila = ventana.tablaLibros.currentRow()
        if fila < 0 or fila >= len(libros_actuales):
            return None
        return libros_actuales[fila]

    def abrir_formulario_libro(libro_editar: dict = None, codigo_inicial: str = ""):
        res_ubicaciones = listar_ubicaciones(rol, id_usuario)
        if not res_ubicaciones["ok"]:
            QMessageBox.warning(ventana, "Ubicaciones", res_ubicaciones["mensaje"])
            return

        ubicaciones = res_ubicaciones["datos"] or []
        if not ubicaciones:
            QMessageBox.warning(
                ventana,
                "Ubicaciones",
                "No hay ubicaciones registradas en la base de datos.",
            )
            return

        dialogo = cargar_ui_fn(RUTA_LIBRO_FORM_UI)
        dialogo.setParent(ventana, Qt.Dialog)

        for u in ubicaciones:
            texto_u = f"Estante {u['estante']} - Fila {u['fila']}"
            dialogo.cmbUbicacion.addItem(texto_u, u["id"])

        es_edicion = libro_editar is not None

        if es_edicion:
            dialogo.setWindowTitle("Editar Libro")
            dialogo.lblTituloFormulario.setText(f"Editar Libro (ID #{libro_editar['id']})")
            dialogo.txtCodigo.setText(str(libro_editar["codigo"]))
            dialogo.txtTitulo.setText(str(libro_editar["titulo"]))
            dialogo.txtAutor.setText(str(libro_editar["autor"]))
            dialogo.spnEdicion.setValue(int(libro_editar["edicion"] or 1))
            dialogo.spnAnio.setValue(int(libro_editar["anio"] or 2026))
            dialogo.spnStock.setValue(int(libro_editar["stock"] or 0))
            dialogo.spnStock.setEnabled(True)
            dialogo.txtSinopsis.setPlainText(str(libro_editar["sinopsis"] or ""))

            idx_ubic = dialogo.cmbUbicacion.findData(libro_editar["idUbicacion"])
            if idx_ubic >= 0:
                dialogo.cmbUbicacion.setCurrentIndex(idx_ubic)
        else:
            dialogo.setWindowTitle("Registrar Nuevo Libro")
            dialogo.lblTituloFormulario.setText("Registrar Nuevo Libro")
            dialogo.txtCodigo.setText(codigo_inicial)
            dialogo.spnStock.setValue(1)
            dialogo.spnStock.setEnabled(False)
            if codigo_inicial:
                dialogo.txtTitulo.setFocus()

        def guardar():
            codigo = dialogo.txtCodigo.text().strip()
            titulo = dialogo.txtTitulo.text().strip()
            autor = dialogo.txtAutor.text().strip()
            edicion = dialogo.spnEdicion.value()
            anio = dialogo.spnAnio.value()
            id_ubicacion = dialogo.cmbUbicacion.currentData()
            stock = dialogo.spnStock.value()
            sinopsis = dialogo.txtSinopsis.toPlainText().strip()

            if es_edicion:
                resultado = editar_libro(
                    rol=rol,
                    id_usuario=id_usuario,
                    id_libro=libro_editar["id"],
                    codigo=codigo,
                    titulo=titulo,
                    autor=autor,
                    edicion=edicion,
                    anio=anio,
                    sinopsis=sinopsis,
                    id_ubicacion=id_ubicacion,
                    stock=stock,
                )
            else:
                resultado = escanear_alta_libro(
                    rol=rol,
                    id_usuario=id_usuario,
                    codigo=codigo,
                    titulo=titulo,
                    autor=autor,
                    edicion=edicion,
                    anio=anio,
                    sinopsis=sinopsis,
                    id_ubicacion=id_ubicacion,
                )

            if not resultado["ok"]:
                QMessageBox.warning(dialogo, "Aviso", resultado["mensaje"])
                return

            QMessageBox.information(dialogo, "Éxito", resultado["mensaje"])
            dialogo.accept()
            cargar_libros(ventana.txtBuscarLibro.text())
            seleccionar_libro_en_tabla_por_codigo(codigo)

        dialogo.btnGuardar.clicked.connect(guardar)
        dialogo.btnCancelar.clicked.connect(dialogo.reject)
        dialogo.exec()

    def procesar_codigo_barras():
        codigo = ventana.txtCodigoBarras.text().strip()
        if not codigo:
            QMessageBox.warning(
                ventana,
                "Código de barras",
                "Escanea o escribe un código de barras.",
            )
            return

        # 1. Buscar si el código ya existe en la base de datos
        res_busqueda = buscar_libro_por_codigo(rol, id_usuario, codigo)

        # Si el usuario es lector, solo busca y muestra el libro
        if not es_personal:
            if res_busqueda["ok"]:
                libro = res_busqueda["datos"]
                poblar_tabla([libro], res_busqueda["mensaje"])
                ventana.tablaLibros.selectRow(0)
                QMessageBox.information(
                    ventana,
                    "Libro encontrado",
                    f"{res_busqueda['mensaje']}\n\n"
                    f"Título: {libro['titulo']}\n"
                    f"Autor: {libro['autor']}\n"
                    f"Ubicación: Estante {libro['estante']} - Fila {libro['fila']}\n"
                    f"Stock disponible: {libro['stock']}",
                )
            else:
                QMessageBox.warning(ventana, "Búsqueda por código", res_busqueda["mensaje"])
            ventana.txtCodigoBarras.clear()
            ventana.txtCodigoBarras.setFocus()
            return

        # 2. Para administrador / empleado:
        # Si el libro ya existe -> alta rápida sumando +1 al stock con escanear_alta_libro
        if res_busqueda["ok"]:
            libro_existente = res_busqueda["datos"]
            res_alta = escanear_alta_libro(rol=rol, id_usuario=id_usuario, codigo=codigo)

            if res_alta["ok"]:
                cargar_libros(ventana.txtBuscarLibro.text())
                seleccionar_libro_en_tabla_por_codigo(codigo)
                QMessageBox.information(
                    ventana,
                    "Stock actualizado (+1)",
                    f"{res_alta['mensaje']}\n\n"
                    f"Libro: {libro_existente['titulo']}\n"
                    f"Nuevo stock: {libro_existente['stock'] + 1}",
                )
            else:
                QMessageBox.warning(ventana, "Error al actualizar stock", res_alta["mensaje"])

            ventana.txtCodigoBarras.clear()
            ventana.txtCodigoBarras.setFocus()
        else:
            # Si el código no existe -> abrir formulario para registrar el nuevo libro
            ventana.txtCodigoBarras.clear()
            abrir_formulario_libro(libro_editar=None, codigo_inicial=codigo)
            ventana.txtCodigoBarras.setFocus()

    def accion_buscar():
        filtro = ventana.txtBuscarLibro.text()
        cargar_libros(filtro)

    def accion_limpiar_busqueda():
        ventana.txtBuscarLibro.clear()
        cargar_libros("")

    def accion_editar():
        libro = obtener_libro_seleccionado()
        if not libro:
            QMessageBox.warning(
                ventana,
                "Selección requerida",
                "Selecciona un libro de la tabla para editar.",
            )
            return
        abrir_formulario_libro(libro_editar=libro)

    def accion_eliminar():
        libro = obtener_libro_seleccionado()
        if not libro:
            QMessageBox.warning(
                ventana,
                "Selección requerida",
                "Selecciona un libro de la tabla para eliminar.",
            )
            return

        confirmacion = QMessageBox.question(
            ventana,
            "Confirmar eliminación",
            f"¿Estás seguro de eliminar el libro '{libro['titulo']}' (Código: {libro['codigo']})?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return

        resultado = eliminar_libro(rol, id_usuario, libro["id"])
        if resultado["ok"]:
            QMessageBox.information(ventana, "Libro eliminado", resultado["mensaje"])
            cargar_libros(ventana.txtBuscarLibro.text())
        else:
            QMessageBox.warning(ventana, "Error al eliminar", resultado["mensaje"])

    # Conectar eventos de buscador
    ventana.btnBuscarLibro.clicked.connect(accion_buscar)
    ventana.txtBuscarLibro.returnPressed.connect(accion_buscar)
    ventana.btnLimpiarBusqueda.clicked.connect(accion_limpiar_busqueda)

    # Conectar eventos de lector de código de barras (returnPressed y botón)
    ventana.txtCodigoBarras.returnPressed.connect(procesar_codigo_barras)
    ventana.btnEscanearLibro.clicked.connect(procesar_codigo_barras)

    # Conectar botones de Nuevo, Editar y Eliminar
    ventana.btnNuevoLibro.clicked.connect(lambda: abrir_formulario_libro(None, ""))
    ventana.btnEditarLibro.clicked.connect(accion_editar)
    ventana.btnEliminarLibro.clicked.connect(accion_eliminar)

    # Cargar catálogo inicial al entrar
    cargar_libros("")
    return lambda: cargar_libros(ventana.txtBuscarLibro.text())
