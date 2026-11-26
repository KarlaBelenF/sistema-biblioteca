import mysql.connector
from src.conexion import obtener_conexion

# Lista todos los libros con sus ubicaciones, opcionalmente filtrando por código, título o autor
# Retorna un diccionario con el resultado de la consulta y un mensaje indicando la cantidad de libros encontrados.
def listar_libros(rol: str, id_usuario: int, filtro: str = "") -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT l.id, l.codigo, l.titulo, l.autor, l.edicion, l.anio,
                   l.sinopsis, l.idUbicacion, u.estante, u.fila, l.stock
            FROM libro l
            JOIN ubicacion u ON l.idUbicacion = u.id
        """
        params = () # params es una tupla vacía que se utilizará para pasar los parámetros a la consulta SQL. Inicialmente está vacía porque no se ha aplicado ningún filtro.
        if filtro.strip(): # Si el filtro no está vacío, se construye un patrón de búsqueda utilizando el operador LIKE de SQL para buscar coincidencias parciales en los campos código, título o autor del libro
            patron = f"%{filtro.strip()}%"
            query += " WHERE l.codigo LIKE %s OR l.titulo LIKE %s OR l.autor LIKE %s"
            params = (patron, patron, patron) # Se asigna la tupla de parámetros con el patrón de búsqueda para cada uno de los campos que se van a filtrar (código, título y autor). Esto permite que la consulta SQL busque coincidencias parciales en cualquiera de esos campos.

        query += " ORDER BY l.titulo ASC;" 
        cursor.execute(query, params)
        filas = cursor.fetchall()

        return {"ok": True, "datos": filas, "mensaje": f"{len(filas)} libro(s) encontrados."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": f"Error al consultar libros: {err.msg}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Busca un libro exacto por código de barras (útil al escanear)
# Retorna un diccionario con el resultado de la búsqueda y un mensaje indicando si se encontró el libro o no.
def buscar_libro_por_codigo(rol: str, id_usuario: int, codigo: str) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT l.id, l.codigo, l.titulo, l.autor, l.edicion, l.anio,
                   l.sinopsis, l.idUbicacion, u.estante, u.fila, l.stock
            FROM libro l
            JOIN ubicacion u ON l.idUbicacion = u.id
            WHERE l.codigo = %s
            LIMIT 1;
        """
        cursor.execute(query, (codigo.strip(),))
        libro = cursor.fetchone()

        if not libro:
            return {"ok": False, "datos": None, "mensaje": "Libro no encontrado."}

        return {"ok": True, "datos": libro, "mensaje": "Libro encontrado."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": f"Error al buscar libro: {err.msg}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Lista estantes y filas disponibles para los formularios. Un formulario de alta o edición de libro necesita conocer las ubicaciones disponibles para asignar un libro a un estante y fila específicos.
# Retorna un diccionario con el resultado de la consulta y un mensaje indicando si se cargaron las ubicaciones correctamente o si hubo un error.
def listar_ubicaciones(rol: str, id_usuario: int) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, estante, fila FROM ubicacion ORDER BY estante, fila;")
        return {"ok": True, "datos": cursor.fetchall(), "mensaje": "Ubicaciones cargadas."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": f"Error al cargar ubicaciones: {err.msg}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Si el código existe suma 1 al stock; si es nuevo lo inserta con stock 1
def escanear_alta_libro(
    rol: str,
    id_usuario: int,
    codigo: str,
    titulo: str = None,
    autor: str = None,
    edicion: int = None,
    anio: int = None,
    sinopsis: str = None,
    id_ubicacion: int = None,
) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor()

        args = [codigo.strip(), titulo, autor, edicion, anio, sinopsis, id_ubicacion, 0] # args es una lista que contiene los parámetros que se pasarán al procedimiento almacenado escanear_alta_libro. El último elemento (0) es un valor de salida que se utilizará para capturar el ID generado o actualizado del libro.
        resultado = cursor.callproc("escanear_alta_libro", args)
        id_generado = resultado[7]

        return {
            "ok": True,
            "datos": {"id": id_generado},
            "mensaje": f"Libro registrado o stock actualizado (ID: {id_generado}).",
        }
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Actualiza los datos de un libro existente (dispara auditoría).
def editar_libro(
    rol: str,
    id_usuario: int,
    id_libro: int,
    codigo: str,
    titulo: str,
    autor: str,
    edicion: int,
    anio: int,
    sinopsis: str,
    id_ubicacion: int,
    stock: int,
) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor()

        query = """
            UPDATE libro
            SET codigo = %s, titulo = %s, autor = %s, edicion = %s,
                anio = %s, sinopsis = %s, idUbicacion = %s, stock = %s
            WHERE id = %s;
        """
        cursor.execute(
            query,
            (codigo.strip(), titulo.strip(), autor.strip(), edicion, anio, sinopsis, id_ubicacion, stock, id_libro),
        )
        conn.commit()

        return {"ok": True, "datos": None, "mensaje": "Libro actualizado correctamente."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Elimina un libro por ID (solo permitido para administrador).
def eliminar_libro(rol: str, id_usuario: int, id_libro: int) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM libro WHERE id = %s;", (id_libro,))
        conn.commit()

        if cursor.rowcount == 0:
            return {"ok": False, "datos": None, "mensaje": "No se encontró el libro."}

        return {"ok": True, "datos": None, "mensaje": "Libro eliminado correctamente."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    print(listar_libros("lector", 3))
    print(buscar_libro_por_codigo("empleado", 2, "9788497592208"))