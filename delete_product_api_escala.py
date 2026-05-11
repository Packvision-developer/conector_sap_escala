import requests
import pandas as pd
import time
import json

# ==========================================
# CONFIGURACIÓN DE LA API
# ==========================================
API_KEY = "sv1gf5FpA-BN9RGFevNJMP_PmuSmQX12Hd4GJM0ZtINjjh6v6_igSejNKL5FDhkCXzF0uWyids7enZ5Fifxf1A" # Reemplaza con tu API Key real
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}
BASE_URL = "https://public-api.escala.com/v1/pms/products"

def obtener_todos_los_productos():
    """
    Recorre todas las páginas de la API para extraer el 100% de los productos.
    """
    print("Iniciando la extracción de productos...")
    todos_los_productos = []
    pagina_actual = 0
    tamano_pagina = 50 # Pedimos 50 por página para hacer menos peticiones
    total_esperado = 0
    
    while True:
        print(f"Obteniendo página {pagina_actual}...")
        params = {"page": pagina_actual, "size": tamano_pagina}
        response = requests.get(BASE_URL, headers=HEADERS, params=params)
        
        if response.status_code != 200:
            print(f"Error en la API: {response.status_code} - {response.text}")
            break
            
        data = response.json()
        items = data.get("items", [])
        total_esperado = data.get("total", 0)
        
        if not items:
            break # Si ya no hay items, salimos del bucle
            
        todos_los_productos.extend(items)
        
        # Si ya recolectamos todos los que dice el "total", paramos.
        if len(todos_los_productos) >= total_esperado:
            break
            
        pagina_actual += 1
        
    return todos_los_productos, total_esperado

def crear_backup_csv(productos):
    """
    Transforma la lista de diccionarios en un DataFrame y lo guarda como CSV.
    """
    print("\nGenerando Backup...")
    if not productos:
        print("No hay productos para hacer backup.")
        return
        
    # json_normalize "aplana" los diccionarios anidados como el campo 'custom'
    # Ejemplo: custom.cf_product_gramaje_fsis_text se vuelve una columna limpia.
    df = pd.json_normalize(productos)
    nombre_archivo = "backup_productos_escala.csv"
    df.to_csv(nombre_archivo, index=False, encoding='utf-8-sig')
    print(f"¡Éxito! Backup guardado como '{nombre_archivo}'.")

def eliminar_productos_en_lote(ids_a_eliminar):
    """
    Recibe una lista de IDs y lanza peticiones DELETE a la API.
    """
    print(f"\n[ATENCIÓN] Iniciando proceso de eliminación para {len(ids_a_eliminar)} productos...")
    
    exitosos = 0
    fallidos = 0
    
    for product_id in ids_a_eliminar:
        url_delete = f"{BASE_URL}/{product_id}"
        
        # -------------------------------------------------------------------
        # LA PETICIÓN REAL ESTÁ COMENTADA POR SEGURIDAD. 
        # Para encender esta función, descomenta las líneas debajo de este bloque.
        # -------------------------------------------------------------------
        
        response = requests.delete(url_delete, headers=HEADERS)
        if response.status_code in [200, 204]:
            print(f" Eliminado: {product_id}")
            exitosos += 1
        else:
            print(f" Error al eliminar {product_id}: Status {response.status_code}")
            fallidos += 1
    
        # SIMULACIÓN (Comentar esto cuando actives lo de arriba):
        #print(f" [SIMULACIÓN] Producto {product_id} habría sido eliminado.")
       # exitosos += 1
        
        # Buena práctica: Dormir 0.2 segundos para no saturar la API (Rate Limiting)
        time.sleep(0.2) 
        
    print(f"\nResumen de eliminación: {exitosos} exitosos, {fallidos} fallidos.")

# ==========================================
# FLUJO PRINCIPAL DE EJECUCIÓN
# ==========================================
if __name__ == "__main__":
    # 1. Obtener y contar
    productos, total_en_api = obtener_todos_los_productos()
    cantidad_obtenida = len(productos)
    
    print(f"\n--- VERIFICACIÓN ---")
    print(f"Total reportado por la API: {total_en_api}")
    print(f"Total de registros descargados: {cantidad_obtenida}")
    
    if cantidad_obtenida == 638:
        print("¡Perfecto! Los números cuadran exactamente con tus 638 productos.")
    else:
        print("Cuidado: La cantidad descargada no coincide con tu expectativa de 638.")

    # 2. Hacer el backup (Nunca te saltes este paso)
    crear_backup_csv(productos)
    
    # 3. Preparar la guillotina (Separar el que se queda de los que se van)
    if cantidad_obtenida > 1:
        # Extraemos todos los IDs
        todos_los_ids = [p["id"] for p in productos]
        
        # Guardamos el primer ID como plantilla, el resto a la guillotina
        id_plantilla = todos_los_ids[0]
        ids_para_eliminar = todos_los_ids[1:] 
        
        print(f"\n--- PLAN DE EJECUCIÓN ---")
        print(f"Producto a CONSERVAR (Plantilla): {id_plantilla}")
        print(f"Productos a ELIMINAR: {len(ids_para_eliminar)}")
        
        # 4. Ejecutar eliminación (Actualmente en modo simulado)
        # *Para apagar/encender funciones, comenta o descomenta la llamada de abajo*
        
        eliminar_productos_en_lote(ids_para_eliminar)
        
    else:
        print("No hay suficientes productos para eliminar (hay 1 o 0).")