import os
import mysql.connector
from dotenv import load_dotenv
from src.conexion import obtener_conexion

load_dotenv()
AES_KEY = os.getenv("AES_KEY", "biblioteca_2026") # Clave para cifrar y descifrar datos sensibles (teléfono y dirección) en la base de datos. Se obtiene de las variables de entorno, con un valor por defecto si no está definida.

# Lista todos los usuarios con teléfono y dirección descifrados (para administrador). 
# Se puede filtrar por correo o nombre. Retorna un diccionario con el resultado de la consulta y un mensaje indicando la cantidad de usuarios encontrados.
def listar_usuarios(rol: str, id_usuario: int, filtro: str = "") -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, correo, nombre,
                   CAST(AES_DECRYPT(telefono, %s) AS CHAR) AS telefono,
                   CAST(AES_DECRYPT(direccion, %s) AS CHAR) AS direccion,
                   rol, activo
            FROM usuario
        """
        params = [AES_KEY, AES_KEY]

        if filtro.strip():
            patron = f"%{filtro.strip()}%"
            query += " WHERE correo LIKE %s OR nombre LIKE %s"
            params.extend([patron, patron])

        query += " ORDER BY id ASC;"
        cursor.execute(query, tuple(params))
        filas = cursor.fetchall()

        return {"ok": True, "datos": filas, "mensaje": f"{len(filas)} usuario(s) encontrados."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Devuelve id, nombre y correo de lectores activos para registrar préstamos.
def listar_lectores_activos(rol: str, id_usuario: int) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol, id_usuario)
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, nombre, correo
            FROM usuario
            WHERE rol = 'lector' AND activo = TRUE
            ORDER BY nombre ASC;
        """
        cursor.execute(query)
        return {"ok": True, "datos": cursor.fetchall(), "mensaje": "Lectores cargados."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Crea un nuevo usuario, cifrando datos sensibles.
def crear_usuario(
    rol_sesion: str,
    id_usuario_sesion: int,
    correo: str,
    contrasenia: str,
    nombre: str,
    telefono: str,
    direccion: str,
    rol_nuevo: str,
) -> dict:
    if not correo.strip() or not contrasenia or not nombre.strip():
        return {"ok": False, "datos": None, "mensaje": "Correo, contraseña y nombre son obligatorios."}

    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol_sesion, id_usuario_sesion)
        cursor = conn.cursor()

        query = """
            INSERT INTO usuario (correo, contrasenia, nombre, telefono, direccion, rol, activo)
            VALUES (%s, SHA2(%s, 256), %s, AES_ENCRYPT(%s, %s), AES_ENCRYPT(%s, %s), %s, TRUE);
        """
        cursor.execute(
            query,
            (
                correo.strip(),
                contrasenia,
                nombre.strip(),
                telefono.strip(),
                AES_KEY,
                direccion.strip(),
                AES_KEY,
                rol_nuevo,
            ),
        )
        conn.commit()
        return {"ok": True, "datos": {"id": cursor.lastrowid}, "mensaje": "Usuario creado correctamente."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Actualiza un usuario existente (dispara auditoría). Si nueva_contrasenia viene vacía, conserva la actual.
def editar_usuario(
    rol_sesion: str,
    id_usuario_sesion: int,
    id_objetivo: int,
    correo: str,
    nombre: str,
    telefono: str,
    direccion: str,
    rol_nuevo: str,
    activo: bool,
    nueva_contrasenia: str = "",
) -> dict:
    conn = None
    cursor = None
    try:
        conn = obtener_conexion(rol_sesion, id_usuario_sesion)
        cursor = conn.cursor()

        if nueva_contrasenia.strip(): 
            query = """
                UPDATE usuario
                SET correo = %s, contrasenia = SHA2(%s, 256), nombre = %s,
                    telefono = AES_ENCRYPT(%s, %s), direccion = AES_ENCRYPT(%s, %s),
                    rol = %s, activo = %s
                WHERE id = %s;
            """
            params = (
                correo.strip(),
                nueva_contrasenia.strip(),
                nombre.strip(),
                telefono.strip(),
                AES_KEY,
                direccion.strip(),
                AES_KEY,
                rol_nuevo,
                activo,
                id_objetivo,
            )
        else:
            query = """
                UPDATE usuario
                SET correo = %s, nombre = %s,
                    telefono = AES_ENCRYPT(%s, %s), direccion = AES_ENCRYPT(%s, %s),
                    rol = %s, activo = %s
                WHERE id = %s;
            """
            params = (
                correo.strip(),
                nombre.strip(),
                telefono.strip(),
                AES_KEY,
                direccion.strip(),
                AES_KEY,
                rol_nuevo,
                activo,
                id_objetivo,
            )

        cursor.execute(query, params)
        conn.commit()
        return {"ok": True, "datos": None, "mensaje": "Usuario actualizado correctamente."}
    except mysql.connector.Error as err:
        return {"ok": False, "datos": None, "mensaje": err.msg}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    print(listar_usuarios("administrador", 1))
    print(listar_lectores_activos("empleado", 2))