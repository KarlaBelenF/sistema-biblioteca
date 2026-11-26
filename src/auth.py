import mysql.connector
from src.conexion import obtener_conexion
# Valida las credenciales de un usuario contra la base de datos
# Se utiliza SHA2(256) para la verificación de la contraseña
# La función retorna un diccionario con el resultado de la validación, incluyendo información del usuario si las credenciales son correctas y el estado de la cuenta.
def iniciar_sesion(correo: str, contrasenia: str) -> dict:
    correo = correo.strip() # Elimina espacios en blanco al inicio y al final del correo
    contrasenia = contrasenia.strip() # Elimina espacios en blanco al inicio y al final de la contraseña
    if not correo or not contrasenia:
        return {"ok": False, "datos": None, "mensaje": "Ingresa correo y contraseña."} # retorna un diccionario indicando que faltan credenciales

    conn = None # Conexion
    cursor = None # Un cursor es un objeto que permite ejecutar consultas SQL y recuperar resultados de la base de datos
    try:
        conn = obtener_conexion("administrador")
        cursor = conn.cursor(dictionary=True) # El parámetro dictionary=True permite que los resultados de las consultas se devuelvan como diccionarios en lugar de tuplas, lo que facilita el acceso a los datos por nombre de columna.

        # consulta SQL para verificar las credenciales del usuario
        query = """ 
            SELECT id, correo, nombre, rol, activo
            FROM usuario
            WHERE correo = %s
              AND contrasenia = SHA2(%s, 256)
            LIMIT 1;
        """
        cursor.execute(query, (correo, contrasenia))
        usuario = cursor.fetchone() # fetchone() obtiene la primera fila del resultado de la consulta, o None si no hay resultados

        if not usuario: # Si no se encuentra un usuario con las credenciales proporcionadas, retorna un diccionario indicando que el correo o la contraseña son incorrectos
            return {"ok": False, "datos": None, "mensaje": "Correo o contraseña incorrectos."}

        if not usuario["activo"]: # Si el usuario existe pero su cuenta está inactiva, retorna un diccionario indicando que la cuenta está inactiva
            return {"ok": False, "datos": None, "mensaje": "Tu cuenta está inactiva."}

        return { # Si las credenciales son correctas y la cuenta está activa, retorna un diccionario con la información del usuario y un mensaje de bienvenida
            "ok": True,
            "datos": {
                "id": usuario["id"],
                "correo": usuario["correo"],
                "nombre": usuario["nombre"],
                "rol": usuario["rol"],
            },
            "mensaje": f"Bienvenido, {usuario['nombre']}.",
        }
    except mysql.connector.Error as err: # Maneja errores de conexión o ejecución de consultas SQL y retorna un diccionario con el mensaje de error
        return {"ok": False, "datos": None, "mensaje": f"Error de base de datos: {err.msg}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__": # Permite probar la función de inicio de sesión ejecutando este archivo directamente
    print(iniciar_sesion("admin@biblioteca.com", "admin123"))
    print(iniciar_sesion("admin@biblioteca.com", "malapass"))