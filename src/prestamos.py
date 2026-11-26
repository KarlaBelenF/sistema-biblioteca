import mysql.connector
from src.conexion import obtener_conexion

# Registra uno o varios libros bajo un mismo folio.
# fecha_limite: 'YYYY-MM-DD HH:MM:SS'
# lista_libros: [{'idLibro': 1, 'cantidad': 1}, ...]
def registrar_prestamo_multiple(
    rol: str,
    id_empleado: int,
    id_lector: int,
    fecha_limite: str,
    lista_libros: list,
) -> dict:
    if not lista_libros:
        return {"ok": False, "datos": None, "mensaje": "Agrega al menos un libro al préstamo."}

    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_empleado)
        cursor = conn.cursor()

        folio_actual = 0 # Se inicializa folio_actual en 0 para que el procedimiento almacenado registrar_prestamo genere un nuevo folio si es la primera iteración del bucle. En cada iteración, el procedimiento devuelve el folio generado o actualizado, que se almacena en folio_actual para la siguiente iteración.
        for item in lista_libros:
            args = [
                folio_actual, 
                id_empleado,
                id_lector,
                fecha_limite,
                item["idLibro"],
                item["cantidad"],
                0,
            ]
            resultado = cursor.callproc("registrar_prestamo", args)
            folio_actual = resultado[6]

        return {
            "ok": True,
            "datos": {"folio": folio_actual},
            "mensaje": f"Préstamo registrado con folio #{folio_actual}.",
        }
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Busca qué lectores tienen prestado actualmente el libro escaneado.
def buscar_prestamos_activos_por_codigo(rol: str, id_usuario: int, codigo: str) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        # Consulta SQL para buscar préstamos activos por código de libro
        query = """ 
            SELECT p.folio, dp.idLibro, l.codigo, l.titulo,
                   u.id AS idLector, u.nombre AS nombreLector,
                   dp.cantidad, p.fechaSalida, p.fechaLimiteDevolucion,
                   calcular_dias_retraso(dp.idPrestamo, dp.idLibro) AS diasRetraso
            FROM detalles_prestamo dp
            JOIN prestamo p ON dp.idPrestamo = p.folio
            JOIN libro l ON dp.idLibro = l.id
            JOIN usuario u ON p.idLector = u.id
            WHERE l.codigo = %s AND dp.estado = 'prestado'
            ORDER BY p.fechaLimiteDevolucion ASC;
        """
        cursor.execute(query, (codigo.strip(),)) 
        filas = cursor.fetchall()

        if not filas:
            return {"ok": False, "datos": [], "mensaje": "No hay préstamos activos para ese código."}

        return {"ok": True, "datos": filas, "mensaje": f"{len(filas)} préstamo(s) activo(s) encontrados."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Marca un libro como devuelto, recupera el stock y devuelve los días de retraso.
def registrar_devolucion(rol: str, id_usuario: int, folio: int, id_libro: int) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor()

        resultado = cursor.callproc("registrar_devolucion", [folio, id_libro, 0])
        dias_retraso = resultado[2]

        texto_retraso = f" con {dias_retraso} día(s) de retraso." if dias_retraso > 0 else " a tiempo."
        return {
            "ok": True,
            "datos": {"dias_retraso": dias_retraso},
            "mensaje": f"Devolución registrada{texto_retraso}",
        }
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Devuelve el historial de préstamos de un lector específico.
def listar_prestamos_lector(rol: str, id_usuario: int, id_lector: int) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT p.folio, l.codigo, l.titulo, dp.cantidad,
                   p.fechaSalida, p.fechaLimiteDevolucion,
                   dp.fechaRealDevolucion, dp.estado,
                   calcular_dias_retraso(dp.idPrestamo, dp.idLibro) AS diasRetraso
            FROM prestamo p
            JOIN detalles_prestamo dp ON p.folio = dp.idPrestamo
            JOIN libro l ON dp.idLibro = l.id
            WHERE p.idLector = %s
            ORDER BY p.fechaSalida DESC;
        """
        cursor.execute(query, (id_lector,))
        return {"ok": True, "datos": cursor.fetchall(), "mensaje": "Historial cargado."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    print(buscar_prestamos_activos_por_codigo("empleado", 2, "9788497592208"))
    print(listar_prestamos_lector("lector", 3, 3))