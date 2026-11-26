import os
import mysql.connector
from dotenv import load_dotenv
from src.conexion import obtener_conexion

load_dotenv()
AES_KEY = os.getenv("AES_KEY", "biblioteca_2026")

# Devuelve los títulos con mayor cantidad de ejemplares prestados.
def reporte_libros_mas_solicitados(rol: str, id_usuario: int, limite: int = 10) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT l.codigo, l.titulo, l.autor, u.estante, u.fila,
                   SUM(dp.cantidad) AS totalEjemplaresPrestados
            FROM libro l
            JOIN ubicacion u ON l.idUbicacion = u.id
            JOIN detalles_prestamo dp ON dp.idLibro = l.id
            GROUP BY l.codigo, l.titulo, l.autor, u.estante, u.fila
            ORDER BY totalEjemplaresPrestados DESC
            LIMIT %s;
        """
        cursor.execute(query, (limite,))
        return {"ok": True, "datos": cursor.fetchall(), "mensaje": "Reporte de libros más solicitados generado."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Devuelve préstamos activos vencidos con teléfono descifrado y días de retraso.
def reporte_prestamos_retrasados(rol: str, id_usuario: int) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT p.folio, u.nombre,
                   CAST(AES_DECRYPT(u.telefono, %s) AS CHAR) AS telefono,
                   l.titulo, dp.cantidad, p.fechaLimiteDevolucion,
                   calcular_dias_retraso(dp.idPrestamo, dp.idLibro) AS diasRetraso
            FROM prestamo p
            JOIN detalles_prestamo dp ON dp.idPrestamo = p.folio
            JOIN libro l ON l.id = dp.idLibro
            JOIN usuario u ON p.idLector = u.id
            WHERE dp.estado = 'prestado'
              AND p.fechaLimiteDevolucion < CURRENT_TIMESTAMP()
            ORDER BY diasRetraso DESC;
        """
        cursor.execute(query, (AES_KEY,))
        return {"ok": True, "datos": cursor.fetchall(), "mensaje": "Reporte de préstamos con retraso generado."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Devuelve el historial de cambios registrados por los triggers de auditoría.
def listar_auditoria(rol: str, id_usuario: int, limite: int = 100) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.id, a.tablaAfectada, a.tipoDeOperacion, a.fecha_hora,
                   IFNULL(u.nombre, 'Sistema / Workbench') AS responsable,
                   a.informacionAnterior, a.informacionNueva
            FROM auditoria a
            LEFT JOIN usuario u ON a.idUsuario = u.id 
            ORDER BY a.fecha_hora DESC
            LIMIT %s;
        """
        cursor.execute(query, (limite,))
        return {"ok": True, "datos": cursor.fetchall(), "mensaje": "Bitácora de auditoría cargada."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    print(reporte_libros_mas_solicitados("administrador", 1))
    print(reporte_prestamos_retrasados("administrador", 1))
    print(listar_auditoria("administrador", 1))