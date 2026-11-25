import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def obtener_conexion(rol="lector", id_usuario=None):
    credenciales = {
        "administrador": (os.getenv("DB_ADMIN_USER"), os.getenv("DB_ADMIN_PASS")),
        "empleado": (os.getenv("DB_EMPLEADO_USER"), os.getenv("DB_EMPLEADO_PASS")),
        "lector": (os.getenv("DB_LECTOR_USER"), os.getenv("DB_LECTOR_PASS")),
    }

    usuario_db, password_db = credenciales.get(rol, credenciales["lector"])

    conexion = mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME", "BIBLIOTECA"),
        user=usuario_db,
        password=password_db,
    )

    if id_usuario is not None:
        cursor = conexion.cursor()
        cursor.execute("SET @usuario_actual = %s;", (id_usuario,))
        cursor.close()

    return conexion

if __name__ == "__main__":
    try:
        conn = obtener_conexion("administrador", id_usuario=1)
        print("Conexión exitosa a MySQL con rol administrador.")
        conn.close()
    except mysql.connector.Error as err:
        print(f"Error de conexión: {err}")