from PySide6.QtCore import QDateTime, QTime, Qt
from PySide6.QtWidgets import QHeaderView, QMessageBox, QTableWidgetItem
from src.libros import buscar_libro_por_codigo
from src.prestamos import (
    buscar_prestamos_activos_por_codigo,
    listar_prestamos_lector,
    registrar_devolucion,
    registrar_prestamo_multiple,
)
from src.usuarios import listar_lectores_activos


def configurar_pagina_prestamos(ventana, sesion: dict, al_actualizar_stock_fn=None):
    rol = sesion.get("rol", "lector")
    id_usuario = sesion.get("id")
    es_personal = rol in ("administrador", "empleado")

    # Estado en memoria para carrito de Nuevo Préstamo y lista de Devoluciones
    carrito_prestamo = []
    prestamos_activos = []

    # Configurar cabeceras de tablas
    header_carrito = ventana.tablaCarritoPrestamo.horizontalHeader()
    header_carrito.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID Libro
    header_carrito.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Código
    header_carrito.setSectionResizeMode(2, QHeaderView.Stretch)           # Título
    header_carrito.setSectionResizeMode(3, QHeaderView.Stretch)           # Autor
    header_carrito.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Stock Disp.
    header_carrito.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Cantidad

    header_dev = ventana.tablaDevoluciones.horizontalHeader()
    header_dev.setSectionResizeMode(0, QHeaderView.ResizeToContents)      # Folio
    header_dev.setSectionResizeMode(1, QHeaderView.ResizeToContents)      # ID Libro
    header_dev.setSectionResizeMode(2, QHeaderView.ResizeToContents)      # Código
    header_dev.setSectionResizeMode(3, QHeaderView.Stretch)               # Título
    header_dev.setSectionResizeMode(4, QHeaderView.ResizeToContents)      # Lector
    header_dev.setSectionResizeMode(5, QHeaderView.ResizeToContents)      # Cantidad
    header_dev.setSectionResizeMode(6, QHeaderView.ResizeToContents)      # Fecha Salida
    header_dev.setSectionResizeMode(7, QHeaderView.ResizeToContents)      # Fecha Límite
    header_dev.setSectionResizeMode(8, QHeaderView.ResizeToContents)      # Días Retraso

    header_mis = ventana.tablaMisPrestamos.horizontalHeader()
    header_mis.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    header_mis.setSectionResizeMode(1, QHeaderView.ResizeToContents)
    header_mis.setSectionResizeMode(2, QHeaderView.Stretch)
    header_mis.setSectionResizeMode(3, QHeaderView.ResizeToContents)
    header_mis.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    header_mis.setSectionResizeMode(5, QHeaderView.ResizeToContents)
    header_mis.setSectionResizeMode(6, QHeaderView.ResizeToContents)
    header_mis.setSectionResizeMode(7, QHeaderView.ResizeToContents)
    header_mis.setSectionResizeMode(8, QHeaderView.ResizeToContents)

    # Configurar fecha límite por defecto (+7 días a las 18:00:00)
    fecha_defecto = QDateTime.currentDateTime().addDays(7)
    fecha_defecto.setTime(QTime(18, 0, 0))
    ventana.dtFechaLimite.setDateTime(fecha_defecto)

    # Mostrar pestañas según el rol:
    # Administrador / Empleado -> 1) 'Nuevo Préstamo' y 2) 'Devoluciones'
    # Lector -> 'Mis Préstamos'
    ventana.tabPrestamos.setTabVisible(0, es_personal)
    ventana.tabPrestamos.setTabVisible(1, es_personal)
    ventana.tabPrestamos.setTabVisible(2, not es_personal)

    # =========================================================================
    # PESTAÑA 1: NUEVO PRÉSTAMO
    # =========================================================================
    def cargar_lectores():
        if not es_personal:
            return
        ventana.cmbLectorPrestamo.clear()
        resultado = listar_lectores_activos(rol, id_usuario)
        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Lectores", resultado["mensaje"])
            return

        lectores = resultado["datos"] or []
        for lector in lectores:
            texto = f"{lector['nombre']} ({lector['correo']})"
            ventana.cmbLectorPrestamo.addItem(texto, lector["id"])

    def actualizar_tabla_carrito():
        ventana.tablaCarritoPrestamo.setRowCount(0)
        total_ejemplares = 0

        for fila_idx, item in enumerate(carrito_prestamo):
            ventana.tablaCarritoPrestamo.insertRow(fila_idx)
            total_ejemplares += item["cantidad"]

            valores = [
                str(item["idLibro"]),
                str(item["codigo"]),
                str(item["titulo"]),
                str(item["autor"]),
                str(item["stock"]),
                str(item["cantidad"]),
            ]

            for col_idx, texto in enumerate(valores):
                celda = QTableWidgetItem(texto)
                if col_idx in (0, 4, 5):
                    celda.setTextAlignment(Qt.AlignCenter)
                ventana.tablaCarritoPrestamo.setItem(fila_idx, col_idx, celda)

        ventana.lblEstadoCarrito.setText(
            f"{len(carrito_prestamo)} título(s) en el carrito ({total_ejemplares} ejemplar(es))."
        )

    def agregar_libro_al_carrito():
        codigo = ventana.txtCodigoPrestamo.text().strip()
        if not codigo:
            QMessageBox.warning(
                ventana,
                "Código vacío",
                "Escanea o escribe el código de barras de un libro.",
            )
            return

        cantidad_agregar = ventana.spnCantidadPrestamo.value()
        res_libro = buscar_libro_por_codigo(rol, id_usuario, codigo)

        if not res_libro["ok"]:
            QMessageBox.warning(ventana, "Libro no encontrado", res_libro["mensaje"])
            ventana.txtCodigoPrestamo.selectAll()
            ventana.txtCodigoPrestamo.setFocus()
            return

        libro = res_libro["datos"]
        stock_disponible = int(libro.get("stock", 0))

        if stock_disponible <= 0:
            QMessageBox.warning(
                ventana,
                "Sin stock",
                f"El libro '{libro['titulo']}' no tiene ejemplares disponibles en stock.",
            )
            ventana.txtCodigoPrestamo.clear()
            ventana.txtCodigoPrestamo.setFocus()
            return

        # Verificar si el libro ya está en el carrito para acumular su cantidad
        for item in carrito_prestamo:
            if item["idLibro"] == libro["id"]:
                nueva_cantidad = item["cantidad"] + cantidad_agregar
                if nueva_cantidad > stock_disponible:
                    QMessageBox.warning(
                        ventana,
                        "Stock insuficiente",
                        f"No puedes agregar {nueva_cantidad} ejemplar(es) de '{libro['titulo']}'. "
                        f"Stock disponible: {stock_disponible}.",
                    )
                    return
                item["cantidad"] = nueva_cantidad
                item["stock"] = stock_disponible
                actualizar_tabla_carrito()
                ventana.txtCodigoPrestamo.clear()
                ventana.spnCantidadPrestamo.setValue(1)
                ventana.txtCodigoPrestamo.setFocus()
                return

        if cantidad_agregar > stock_disponible:
            QMessageBox.warning(
                ventana,
                "Stock insuficiente",
                f"La cantidad solicitada ({cantidad_agregar}) supera el stock disponible "
                f"({stock_disponible}) para '{libro['titulo']}'.",
            )
            return

        carrito_prestamo.append(
            {
                "idLibro": libro["id"],
                "codigo": libro["codigo"],
                "titulo": libro["titulo"],
                "autor": libro["autor"],
                "stock": stock_disponible,
                "cantidad": cantidad_agregar,
            }
        )
        actualizar_tabla_carrito()
        ventana.txtCodigoPrestamo.clear()
        ventana.spnCantidadPrestamo.setValue(1)
        ventana.txtCodigoPrestamo.setFocus()

    def quitar_seleccionado_carrito():
        fila = ventana.tablaCarritoPrestamo.currentRow()
        if fila < 0 or fila >= len(carrito_prestamo):
            QMessageBox.warning(
                ventana,
                "Selección requerida",
                "Selecciona un libro del carrito para quitarlo.",
            )
            return
        carrito_prestamo.pop(fila)
        actualizar_tabla_carrito()

    def vaciar_carrito():
        carrito_prestamo.clear()
        actualizar_tabla_carrito()

    def confirmar_prestamo():
        if ventana.cmbLectorPrestamo.count() == 0:
            QMessageBox.warning(
                ventana,
                "Lector requerido",
                "No hay lectores activos seleccionados.",
            )
            return

        if not carrito_prestamo:
            QMessageBox.warning(
                ventana,
                "Carrito vacío",
                "Agrega al menos un libro al carrito antes de confirmar el préstamo.",
            )
            return

        id_lector = ventana.cmbLectorPrestamo.currentData()
        fecha_limite = ventana.dtFechaLimite.dateTime().toString("yyyy-MM-dd HH:mm:ss")

        # Formato exacto esperado por src.prestamos.registrar_prestamo_multiple:
        # [{'idLibro': 1, 'cantidad': 1}, ...]
        lista_libros = [
            {"idLibro": item["idLibro"], "cantidad": item["cantidad"]}
            for item in carrito_prestamo
        ]

        resultado = registrar_prestamo_multiple(
            rol=rol,
            id_empleado=id_usuario,
            id_lector=id_lector,
            fecha_limite=fecha_limite,
            lista_libros=lista_libros,
        )

        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Error al registrar préstamo", resultado["mensaje"])
            return

        folio = resultado["datos"]["folio"]
        QMessageBox.information(
            ventana,
            "Préstamo registrado",
            f"{resultado['mensaje']}\n\nFolio asignado: #{folio}",
        )

        vaciar_carrito()
        if al_actualizar_stock_fn:
            al_actualizar_stock_fn()
        ventana.txtCodigoPrestamo.setFocus()

    # =========================================================================
    # PESTAÑA 2: DEVOLUCIONES
    # =========================================================================
    def poblar_tabla_devoluciones(filas: list, mensaje: str = ""):
        nonlocal prestamos_activos
        prestamos_activos = filas or []
        ventana.tablaDevoluciones.setRowCount(0)

        for fila_idx, prestamo in enumerate(prestamos_activos):
            ventana.tablaDevoluciones.insertRow(fila_idx)

            valores = [
                str(prestamo["folio"]),
                str(prestamo["idLibro"]),
                str(prestamo["codigo"]),
                str(prestamo["titulo"]),
                str(prestamo["nombreLector"]),
                str(prestamo["cantidad"]),
                str(prestamo["fechaSalida"]),
                str(prestamo["fechaLimiteDevolucion"]),
                str(prestamo["diasRetraso"]),
            ]

            for col_idx, texto in enumerate(valores):
                celda = QTableWidgetItem(texto)
                if col_idx in (0, 1, 5, 8):
                    celda.setTextAlignment(Qt.AlignCenter)
                ventana.tablaDevoluciones.setItem(fila_idx, col_idx, celda)

        if prestamos_activos:
            ventana.tablaDevoluciones.selectRow(0)

        if mensaje:
            ventana.lblEstadoDevoluciones.setText(mensaje)

    def buscar_prestamos_por_codigo(mostrar_alerta_vacio: bool = True):
        codigo = ventana.txtCodigoDevolucion.text().strip()
        if not codigo:
            QMessageBox.warning(
                ventana,
                "Código requerido",
                "Escanea o escribe el código de barras del libro a devolver.",
            )
            return

        resultado = buscar_prestamos_activos_por_codigo(
            rol=rol,
            id_usuario=id_usuario,
            codigo=codigo,
        )

        if not resultado["ok"]:
            poblar_tabla_devoluciones([], resultado["mensaje"])
            if mostrar_alerta_vacio:
                QMessageBox.information(ventana, "Devoluciones", resultado["mensaje"])
            ventana.txtCodigoDevolucion.selectAll()
            ventana.txtCodigoDevolucion.setFocus()
            return

        poblar_tabla_devoluciones(resultado["datos"], resultado["mensaje"])

    def ejecutar_devolucion():
        fila = ventana.tablaDevoluciones.currentRow()
        if fila < 0 or fila >= len(prestamos_activos):
            QMessageBox.warning(
                ventana,
                "Selección requerida",
                "Selecciona un préstamo activo de la tabla para registrar su devolución.",
            )
            return

        prestamo = prestamos_activos[fila]
        folio = prestamo["folio"]
        id_libro = prestamo["idLibro"]

        resultado = registrar_devolucion(
            rol=rol,
            id_usuario=id_usuario,
            folio=folio,
            id_libro=id_libro,
        )

        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Error al devolver", resultado["mensaje"])
            return

        dias_retraso = resultado["datos"]["dias_retraso"]
        QMessageBox.information(
            ventana,
            "Devolución exitosa",
            f"{resultado['mensaje']}\n\n"
            f"Folio: #{folio}\n"
            f"Libro: {prestamo['titulo']}\n"
            f"Lector: {prestamo['nombreLector']}\n"
            f"Días de retraso: {dias_retraso}",
        )

        if al_actualizar_stock_fn:
            al_actualizar_stock_fn()

        # Refrescar la tabla de devoluciones para ese código
        if ventana.txtCodigoDevolucion.text().strip():
            buscar_prestamos_por_codigo(mostrar_alerta_vacio=False)
        else:
            poblar_tabla_devoluciones([], "Devolución registrada.")
        ventana.txtCodigoDevolucion.setFocus()

    # =========================================================================
    # PESTAÑA 3: MIS PRÉSTAMOS (SOLO PARA ROL LECTOR)
    # =========================================================================
    def cargar_mis_prestamos():
        if es_personal:
            return
        resultado = listar_prestamos_lector(rol, id_usuario, id_usuario)
        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Mis Préstamos", resultado["mensaje"])
            return

        filas = resultado["datos"] or []
        ventana.tablaMisPrestamos.setRowCount(0)
        for fila_idx, p in enumerate(filas):
            ventana.tablaMisPrestamos.insertRow(fila_idx)
            fecha_dev = (
                str(p["fechaRealDevolucion"])
                if p["fechaRealDevolucion"] is not None
                else "Pendiente"
            )
            valores = [
                str(p["folio"]),
                str(p["codigo"]),
                str(p["titulo"]),
                str(p["cantidad"]),
                str(p["fechaSalida"]),
                str(p["fechaLimiteDevolucion"]),
                fecha_dev,
                str(p["estado"]),
                str(p["diasRetraso"]),
            ]
            for col_idx, texto in enumerate(valores):
                celda = QTableWidgetItem(texto)
                if col_idx in (0, 3, 7, 8):
                    celda.setTextAlignment(Qt.AlignCenter)
                ventana.tablaMisPrestamos.setItem(fila_idx, col_idx, celda)

    # Conectar eventos de Pestaña 1 (Nuevo Préstamo)
    ventana.btnRecargarLectores.clicked.connect(cargar_lectores)
    ventana.txtCodigoPrestamo.returnPressed.connect(agregar_libro_al_carrito)
    ventana.btnAgregarCarrito.clicked.connect(agregar_libro_al_carrito)
    ventana.btnQuitarLibroCarrito.clicked.connect(quitar_seleccionado_carrito)
    ventana.btnLimpiarCarrito.clicked.connect(vaciar_carrito)
    ventana.btnConfirmarPrestamo.clicked.connect(confirmar_prestamo)

    # Conectar eventos de Pestaña 2 (Devoluciones)
    ventana.txtCodigoDevolucion.returnPressed.connect(
        lambda: buscar_prestamos_por_codigo(True)
    )
    ventana.btnBuscarDevolucion.clicked.connect(
        lambda: buscar_prestamos_por_codigo(True)
    )
    ventana.btnRegistrarDevolucion.clicked.connect(ejecutar_devolucion)

    # Conectar evento de Pestaña 3 (Mis Préstamos - Lector)
    ventana.btnActualizarMisPrestamos.clicked.connect(cargar_mis_prestamos)

    # Carga inicial según el rol
    if es_personal:
        ventana.tabPrestamos.setCurrentIndex(0)
        cargar_lectores()
    else:
        ventana.tabPrestamos.setCurrentIndex(2)
        cargar_mis_prestamos()

    return cargar_lectores
