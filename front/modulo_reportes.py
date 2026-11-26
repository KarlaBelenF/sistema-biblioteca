from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QMessageBox, QTableWidgetItem
from src.reportes import (
    listar_auditoria,
    reporte_libros_mas_solicitados,
    reporte_prestamos_retrasados,
)


def configurar_pagina_reportes(ventana, sesion: dict):
    rol = sesion.get("rol", "lector")
    id_usuario = sesion.get("id")
    es_personal = rol in ("administrador", "empleado")

    if not es_personal:
        return

    # 1. Configurar columnas de Pestaña 1: Libros más solicitados
    h_solicitados = ventana.tablaMasSolicitados.horizontalHeader()
    h_solicitados.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Código
    h_solicitados.setSectionResizeMode(1, QHeaderView.Stretch)           # Título
    h_solicitados.setSectionResizeMode(2, QHeaderView.Stretch)           # Autor
    h_solicitados.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Estante
    h_solicitados.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Fila
    h_solicitados.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Total Prestados

    # 2. Configurar columnas de Pestaña 2: Préstamos con retraso
    h_retrasados = ventana.tablaPrestamosRetrasados.horizontalHeader()
    h_retrasados.setSectionResizeMode(0, QHeaderView.ResizeToContents)   # Folio
    h_retrasados.setSectionResizeMode(1, QHeaderView.ResizeToContents)   # Lector
    h_retrasados.setSectionResizeMode(2, QHeaderView.ResizeToContents)   # Teléfono
    h_retrasados.setSectionResizeMode(3, QHeaderView.Stretch)            # Libro
    h_retrasados.setSectionResizeMode(4, QHeaderView.ResizeToContents)   # Cantidad
    h_retrasados.setSectionResizeMode(5, QHeaderView.ResizeToContents)   # Fecha Límite
    h_retrasados.setSectionResizeMode(6, QHeaderView.ResizeToContents)   # Días Retraso

    # 3. Configurar columnas de Pestaña 3: Bitácora de Auditoría
    h_auditoria = ventana.tablaAuditoria.horizontalHeader()
    h_auditoria.setSectionResizeMode(0, QHeaderView.ResizeToContents)    # ID
    h_auditoria.setSectionResizeMode(1, QHeaderView.ResizeToContents)    # Tabla Afectada
    h_auditoria.setSectionResizeMode(2, QHeaderView.ResizeToContents)    # Operación
    h_auditoria.setSectionResizeMode(3, QHeaderView.ResizeToContents)    # Fecha y Hora
    h_auditoria.setSectionResizeMode(4, QHeaderView.ResizeToContents)    # Responsable
    h_auditoria.setSectionResizeMode(5, QHeaderView.Stretch)             # Info Anterior
    h_auditoria.setSectionResizeMode(6, QHeaderView.Stretch)             # Info Nueva

    def cargar_libros_mas_solicitados():
        resultado = reporte_libros_mas_solicitados(rol=rol, id_usuario=id_usuario)
        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Reportes", resultado["mensaje"])
            return

        filas = resultado["datos"] or []
        ventana.tablaMasSolicitados.setRowCount(0)

        for fila_idx, item in enumerate(filas):
            ventana.tablaMasSolicitados.insertRow(fila_idx)
            valores = [
                str(item["codigo"]),
                str(item["titulo"]),
                str(item["autor"]),
                str(item["estante"]),
                str(item["fila"]),
                str(item["totalEjemplaresPrestados"]),
            ]
            for col_idx, texto in enumerate(valores):
                celda = QTableWidgetItem(texto)
                if col_idx in (3, 4, 5):
                    celda.setTextAlignment(Qt.AlignCenter)
                ventana.tablaMasSolicitados.setItem(fila_idx, col_idx, celda)

        ventana.lblEstadoSolicitados.setText(
            f"{resultado['mensaje']} ({len(filas)} registro(s))."
        )

    def cargar_prestamos_retrasados():
        resultado = reporte_prestamos_retrasados(rol=rol, id_usuario=id_usuario)
        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Reportes", resultado["mensaje"])
            return

        filas = resultado["datos"] or []
        ventana.tablaPrestamosRetrasados.setRowCount(0)

        for fila_idx, item in enumerate(filas):
            ventana.tablaPrestamosRetrasados.insertRow(fila_idx)
            valores = [
                str(item["folio"]),
                str(item["nombre"]),
                str(item["telefono"] if item["telefono"] is not None else ""),
                str(item["titulo"]),
                str(item["cantidad"]),
                str(item["fechaLimiteDevolucion"]),
                str(item["diasRetraso"]),
            ]
            for col_idx, texto in enumerate(valores):
                celda = QTableWidgetItem(texto)
                if col_idx in (0, 4, 6):
                    celda.setTextAlignment(Qt.AlignCenter)
                ventana.tablaPrestamosRetrasados.setItem(fila_idx, col_idx, celda)

        ventana.lblEstadoRetrasados.setText(
            f"{resultado['mensaje']} ({len(filas)} préstamo(s) con retraso)."
        )

    def cargar_auditoria():
        resultado = listar_auditoria(rol=rol, id_usuario=id_usuario)
        if not resultado["ok"]:
            QMessageBox.warning(ventana, "Auditoría", resultado["mensaje"])
            return

        filas = resultado["datos"] or []
        ventana.tablaAuditoria.setRowCount(0)

        for fila_idx, item in enumerate(filas):
            ventana.tablaAuditoria.insertRow(fila_idx)
            info_ant = (
                str(item["informacionAnterior"])
                if item["informacionAnterior"] is not None
                else "N/A"
            )
            info_nueva = (
                str(item["informacionNueva"])
                if item["informacionNueva"] is not None
                else "N/A"
            )

            valores = [
                str(item["id"]),
                str(item["tablaAfectada"]),
                str(item["tipoDeOperacion"]),
                str(item["fecha_hora"]),
                str(item["responsable"]),
                info_ant,
                info_nueva,
            ]
            for col_idx, texto in enumerate(valores):
                celda = QTableWidgetItem(texto)
                if col_idx in (0, 1, 2):
                    celda.setTextAlignment(Qt.AlignCenter)
                if col_idx in (5, 6):
                    celda.setToolTip(texto)
                ventana.tablaAuditoria.setItem(fila_idx, col_idx, celda)

        ventana.lblEstadoAuditoria.setText(
            f"{resultado['mensaje']} ({len(filas)} evento(s) registrados)."
        )

    def actualizar_todos_los_reportes():
        cargar_libros_mas_solicitados()
        cargar_prestamos_retrasados()
        cargar_auditoria()

    # Conectar botones de Actualizar en cada una de las 3 pestañas
    ventana.btnActualizarSolicitados.clicked.connect(cargar_libros_mas_solicitados)
    ventana.btnActualizarRetrasados.clicked.connect(cargar_prestamos_retrasados)
    ventana.btnActualizarAuditoria.clicked.connect(cargar_auditoria)

    # Carga inicial de las 3 pestañas
    actualizar_todos_los_reportes()
    return actualizar_todos_los_reportes
