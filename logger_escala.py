import os
from datetime import datetime

def registrar_evento(mensaje: str):
    """
    Captura un mensaje, le estampa la hora exacta y lo guarda en el historial.
    """
    directorio_script = os.path.dirname(os.path.abspath(__file__))
    
    tiempo_exacto = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea_log = f"[{tiempo_exacto}] {mensaje}\n"
    ruta_archivo = os.path.join(directorio_script, "historial_mutaciones.log")
    
    with open(ruta_archivo, "a", encoding="utf-8") as archivo:
        archivo.write(linea_log)
        
    print(mensaje) # Mantenemos el eco en consola para depuración local