import pandas as pd
import re
import numpy as np
from SAPServiceLayer import SAPServiceLayerV2 
from EscalaIntegrator import EscalaIntegrator
from Escala_base_agent import EscalaKnowledgeBaseAgent
from logger_escala import registrar_evento
import os

CATALOGO_EMPAQUES = {
    "4PRO": {
        "125": {"precios": {"mate": 610, "brillante": 610, "papel": 610}, "min": 100, "estructura": "115gr/m2"},
        "250": {"precios": {"mate": 1050, "brillante": 940, "papel": 1050}, "min": 50, "estructura": "115gr/m2"},
        "340": {"precios": {"mate": 1100, "brillante": 1100, "papel": 1100}, "min": 50, "estructura": "115gr/m2"},
        "500": {"precios": {"mate": 1210, "brillante": 1160, "papel": 1210}, "min": 50, "estructura": "115gr/m2"},
        "1000": {"precios": {"mate": 1830, "brillante": 1830, "papel": 1830}, "min": 30, "estructura": "115gr/m2"},
        "2500": {"precios": {"mate": 2960, "brillante": 2910, "papel": 2960}, "min": 30, "estructura": "115gr/m2"},
        "125_delgada": {"precios": {"mate": 470, "brillante": 440}, "min": 100, "estructura": "87gr/m2"},
        "250_delgada": {"precios": {"mate": 640, "brillante": 610}, "min": 50, "estructura": "87gr/m2"},
        "500_delgada": {"precios": {"mate": 780, "brillante": 760}, "min": 50, "estructura": "87gr/m2"}
    },
    "DOYPACK": {
        "50": {"precios": {"mate": 580, "brillante": 580, "papel": 580}, "min": 100, "estructura": "115gr/m2"},
        "70": {"precios": {"mate": 630, "brillante": 610, "papel": 630}, "min": 100, "estructura": "115gr/m2"},
        "125": {"precios": {"mate": 910, "brillante": 900, "papel": 910}, "min": 50, "estructura": "115gr/m2"},
        "250": {"precios": {"mate": 1090, "brillante": 1070, "papel": 1090}, "min": 50, "estructura": "115gr/m2"},
        "500": {"precios": {"mate": 1310, "brillante": 1260, "papel": 1310}, "min": 50, "estructura": "115gr/m2"},
        "1000": {"precios": {"mate": 2140, "brillante": 2080, "papel": 2140}, "min": 50, "estructura": "115gr/m2"},
        "2500": {"precios": {"mate": 3530, "brillante": 3250, "papel": 3530}, "min": 30, "estructura": "115gr/m2"}
    },
    "5PRO": {
        "250": {"precios": {"con_zipper": 1540, "sin_zipper": 1320}, "min": 50},
        "340": {"precios": {"con_zipper": 1595, "sin_zipper": 1375}, "min": 50},
        "500": {"precios": {"con_zipper": 1705, "sin_zipper": 1485}, "min": 50},
        "1000": {"precios": {"con_zipper": 2420, "sin_zipper": 2145}, "min": 50},
        "2500": {"precios": {"con_zipper": 3850, "sin_zipper": 3520}, "min": 30}
    },
    "COJIN": {
        "5000": {"precios": {"mate": 5056, "brillante": 5028, "papel": 5028}, "min": 30},
        "PEQUEÑA": {"precios": {"mate": 35323, "brillante": 35323, "papel": 35323}, "min": 100}, 
        "24X30": {"precios": {"brillante": 1000}, "min": 100}
    },
    "SACHET": {
        "FILTRO": {"precios": {"brillante": 33950}, "min": 100},
        "70": {"precios": {"brillante": 42250}, "min": 100}
    },
    "ACCESORIOS": {
        "VALVULA": 440,
        "PEEL": {
            "MONOCROMATICO": 495,
            "COLOR": 580 
        }
    }
}

CATALOGO_COLORES = {
    "AZUL AGUA MARINA": "AZUL AGUA MARINA", "AZUL INSTITUCIONAL": "AZUL INSTITUCIONAL",
    "VERDE MANZANA": "VERDE MANZANA", "VERDE HOJA": "VERDE HOJA",
    "DECEMBRINA ROJO": "DECEMBRINA ROJO", "ROJO LECHOSA": "ROJO LECHOSA",
    "GRANO DE CAFE BEIGE": "GRANO DE CAFE BEIGE", "GRANO DE CAFE ROJO": "GRANO DE CAFE ROJO",
    "GRANO DE CAFE NARANJA": "GRANO DE CAFE NARANJA", "GRAN CAFE NARANJA": "GRAN CAFE NARANJA",
    "NATURAL ENVEJECIDA": "NATURAL ENVEJECIDA", "NATURAL COSTAL": "NATURAL COSTAL",
    "NATURAL ROJO": "NATURAL ROJO", "NATURAL TIPO TRONCO": "NATURAL TIPO TRONCO",
    "BARROCO NATURAL": "BARROCO NATURAL", "BLANCO VERDE": "BLANCO VERDE",
    "FUELLE DORADOS NEGRO": "FUELLE DORADOS NEGRO", "AZUL": "AZUL", "ROJO": "ROJO",
    "VERDE": "VERDE", "BLANCO": "BLANCO", "NEGRO": "NEGRO", "NATURAL": "NATURAL",
    "DORADO": "DORADO", "METALIZADO": "METALIZADO", "METALIZADA": "METALIZADA",
    "NARANJA": "NARANJA", "TRANSPARENTE": "TRANSPARENTE", "VINOTINTO": "VINOTINTO",
    "KRAFT": "KRAFT", "BEIGE": "BEIGE", "AMARILLO": "AMARILLO", "ROSADO": "ROSADO",
    "MORADO": "MORADO", "GRIS": "GRIS", "CAFE": "CAFE", "FUCSIA": "FUCSIA",
    "LILA": "LILA", "TURQUESA": "TURQUESA", "SALMON": "SALMON", "CELESTE": "CELESTE",
    "MOSTAZA": "MOSTAZA", "HOLOGRAFICA": "HOLOGRAFICA", "HOLOGRAFICO": "HOLOGRAFICO",
    "COBRE": "COBRE", "PLATA": "PLATA", "MADERA": "MADERA", "PIEL": "PIEL",
    "CAQUI": "CAQUI", "ORO": "ORO", "BRONCE": "BRONCE", "PURPURA": "PURPURA",
    "MARRON": "MARRON", "VERDE LIMON": "VERDE LIMON", "VERDE OLIVA": "VERDE OLIVA",
    "AZUL OSCURO": "AZUL OSCURO", "AZUL CLARO": "AZUL CLARO", "ROJO VINO": "ROJO VINO",
    "VINO TINTO": "VINO TINTO", "PASTEL JADE VERDE": "PASTEL JADE VERDE",
    "PASTEL MARGALIT AMARILLO": "PASTEL MARGALIT AMARILLO", 
    "PASTEL VERED ROSADO": "PASTEL VERED ROSADO", "PASTEL JADE": "PASTEL JADE",
    "PASTEL SHOSANA LILA": "PASTEL SHOSANA LILA", 
    "PASTEL MARGALITH AMARILLO": "PASTEL MARGALITH AMARILLO",
    "PASTEL VERED": "PASTEL VERED", "AMARILLO COLOMBIA": "AMARILLO COLOMBIA",
    "BELLA BLANCO": "BELLA BLANCO", "BELLA ROJO": "BELLA ROJO", 
    "CAFE OSCURO": "CAFE OSCURO", "CURUBA": "CURUBA", "BARROCO DORADO": "BARROCO DORADO",
    "BARROCO ROJO": "BARROCO ROJO", "BARROCO NEGRO": "BARROCO NEGRO", 
    "TEXTURA CUERO VERDE MENTA": "TEXTURA CUERO VERDE MENTA",
    "TEXTURA CUERO MORADO OSCURO": "TEXTURA CUERO MORADO OSCURO",
    "TEXTURA CUERO AZUL OSCURO": "TEXTURA CUERO AZUL OSCURO",
    "TEXTURA CUERO BLANCO": "TEXTURA CUERO BLANCO", "TEXTURA CUERO": "TEXTURA CUERO",
    "DORADO COBRE HOLOGRAFICO": "DORADO COBRE HOLOGRAFICO",
    "METALIZADO HOLOGRAFICO": "METALIZADO HOLOGRAFICO", 
    "METALIZADO HOLOGRAFICA": "METALIZADO HOLOGRAFICA",
    "NARANJA HOLOGRAFICA": "NARANJA HOLOGRAFICA", "ROJO HOLOGRAFICA": "ROJO HOLOGRAFICA",
    "AZUL HOLOGRAFICA": "AZUL HOLOGRAFICA", 
    "GRAN CAFE NARANJA HOLOGRAFICA": "GRAN CAFE NARANJA HOLOGRAFICA",
    "GRANO DE CAFE NARANJA HOLOGRAFICA": "GRANO DE CAFE NARANJA HOLOGRAFICA",
    "BEIGE BLANCO VERDE": "BEIGE BLANCO VERDE", "BLANCO ROJO": "BLANCO ROJO",
    "NATURAL NEGRO": "NATURAL NEGRO", "SULFITO AMARILLO": "SULFITO AMARILLO",
    "ROSA DE SHARON VERED (ROSADA)": "ROSA DE SHARON VERED (ROSADA)",
    "ROSA DE SHARON VERED": "ROSA DE SHARON VERED",
    "ROSA DE SHARON MARGALIT (AMARILLO)": "ROSA DE SHARON MARGALIT (AMARILLO)",
    "ROSA DE SHARON MARGALIT": "ROSA DE SHARON MARGALIT",
    "ROSA DE SHARON CLAVELINA (BLANCO)": "ROSA DE SHARON CLAVELINA (BLANCO)",
    "ROSA DE SHARON CLAVELINA": "ROSA DE SHARON CLAVELINA",
    "ROSA DE SHARON JADE (VERDE)": "ROSA DE SHARON JADE (VERDE)",
    "ROSA DE SHARON JADE": "ROSA DE SHARON JADE",
    "ROSA DE SHARON LOBELIA (AZUL)": "ROSA DE SHARON LOBELIA (AZUL)",
    "ROSA DE SHARON LOBELIA": "ROSA DE SHARON LOBELIA",
    "ROSA DE SHARON SHOSHANA (MORADA)": "ROSA DE SHARON SHOSHANA (MORADA)",
    "ROSA DE SHARON SHOSHANA": "ROSA DE SHARON SHOSHANA",
    "NEGRO POLYESTER": "NEGRO POLYESTER", "NARANJA LECHOSO": "NARANJA LECHOSO",
    "DECEMBRINA VERDE": "DECEMBRINA VERDE", "GRANO DE CAFÉ BEIGE": "GRANO DE CAFÉ BEIGE",
    "GRANO DE CAFÉ": "GRANO DE CAFÉ", "NEGRO RPD": "NEGRO RPD",
    "BOPP TRANSPARENTE": "BOPP TRANSPARENTE",
    "DORADO CON VISOS (EFECTOS)": "DORADO CON VISOS (EFECTOS)",
    "DORADO CON VISOS": "DORADO CON VISOS", "NEGRO BILLANTE": "NEGRO BILLANTE"
}
CATALOGO_EMPAQUES["FLOWPACK"] = CATALOGO_EMPAQUES["4PRO"]

# ==========================================
# 1. MÓDULO DE EXTRACCIÓN (EXTRACT)
# ==========================================
def extraer_datos(ruta_archivo: str) -> pd.DataFrame:
    try:
        return pd.read_csv(ruta_archivo, sep=',')
    except FileNotFoundError:
        raise FileNotFoundError(f"Error de I/O: El archivo {ruta_archivo} no se encuentra en la ruta.")
    except pd.errors.EmptyDataError:
        raise ValueError("El archivo CSV existe pero está vacío. SAP no retornó datos.")

# ==========================================
# FUNCIONES DE PRICING
# ==========================================
def extraer_atributos_precio(df: pd.DataFrame) -> pd.DataFrame:
    df['Gramaje_Numerico'] = df['Gramaje'].astype(str).str.replace(r'\D+', '', regex=True)
    df['Tiene_Valvula'] = df['ItemName'].str.contains(r'KIT VAL', case=False, na=False)
    df['Tiene_Peel'] = df['ItemName'].str.contains(r'PEEL', case=False, na=False)

    def inferir_color_peel(row):
        if not row['Tiene_Peel']: return 'NO_APLICA'
        texto = str(row['ItemName']).upper()
        if 'COLOR' in texto: return 'COLOR'
        return 'MONOCROMATICO'
        
    df['Color_Peel_Calculado'] = df.apply(inferir_color_peel, axis=1)

    def inferir_terminado(row):
        texto = str(row.get('Resto', '')).upper()
        tipo = str(row.get('Tipo', '')).upper()
        
        if tipo == '5PRO':
            if 'SIN ZIPPER' in texto or 'SIN ZIPER' in texto: return 'sin_zipper'
            elif 'ZIPPER' in texto or 'ZIPER' in texto: return 'con_zipper'
            else: return 'sin_zipper' 
        else:
            if 'MATE' in texto: return 'mate'
            if 'BRILLANTE' in texto or 'BRILL' in texto: return 'brillante'
            if 'PAPEL' in texto or 'KRAFT' in texto: return 'papel'
            
        return 'no_definido'

    df['Terminado_Calculado'] = df.apply(inferir_terminado, axis=1)
    df['Es_Delgada'] = df['Resto'].fillna('').str.upper().str.contains('DELGADA', regex=False)
    return df


def aplicar_pricing(df: pd.DataFrame) -> pd.DataFrame:
    def calcular_fila(row):
        tipo = str(row.get('Tipo')).upper()
        gramaje_num = str(row.get('Gramaje_Numerico'))
        terminado = str(row.get('Terminado_Calculado'))
        es_delgada = bool(row.get('Es_Delgada'))
        
        if tipo not in CATALOGO_EMPAQUES:
            return pd.Series({'Precio': 0, 'Unidades_Minimas': 0, 'Info_Precio': 'Tipo no en Catálogo'})
            
        diccionario_tipo = CATALOGO_EMPAQUES[tipo]
        
        llave_busqueda = gramaje_num
        if tipo in ['4PRO', 'FLOWPACK'] and es_delgada:
             llave_potencial = f"{gramaje_num}_delgada"
             if llave_potencial in diccionario_tipo:
                 llave_busqueda = llave_potencial
                 
        if llave_busqueda not in diccionario_tipo:
             return pd.Series({'Precio': 0, 'Unidades_Minimas': 0, 'Info_Precio': 'Gramaje no en Catálogo'})

        info_empaque = diccionario_tipo[llave_busqueda]
        minimos = info_empaque.get('min', 0)
        precio_base = info_empaque.get('precios', {}).get(terminado, 0)
        
        valor_valvula = 0
        if row.get('Tiene_Valvula'):
            valor_valvula = CATALOGO_EMPAQUES["ACCESORIOS"]["VALVULA"]
            
        valor_peel = 0
        if row.get('Tiene_Peel'):
            color_detectado = row.get(f'Color_Peel_Calculado')
            valor_peel = CATALOGO_EMPAQUES["ACCESORIOS"]["PEEL"].get(color_detectado, 580)
            
        precio_final = precio_base + valor_valvula + valor_peel
        
        estado = 'OK' if precio_base > 0 else f'Terminado {terminado} no encontrado'
        if valor_valvula > 0 or valor_peel > 0:
            estado += ' (+Accesorios Incluidos)'
        
        return pd.Series({'Precio': precio_final, 'Unidades_Minimas': minimos, 'Info_Precio': estado})

    df[['Precio', 'Unidades_Minimas', 'Info_Precio']] = df.apply(calcular_fila, axis=1)
    
    columnas_a_borrar = [
        'Gramaje_Numerico', 'Es_Delgada', 'Terminado_Calculado', 
        'Tiene_Valvula', 'Tiene_Peel', 'Color_Peel_Calculado'
    ]
    df.drop(columns=columnas_a_borrar, inplace=True, errors='ignore')
    return df

# ==========================================
# 2. MÓDULO DE TRANSFORMACIÓN (TRANSFORM)
# ==========================================
def transformar_datos(df_crudo: pd.DataFrame) -> pd.DataFrame:
    df_sap = df_crudo.copy()

    df_sap['Gramaje'] = df_sap['ItemName'].str.extract(r'([\d\.,\-]+\s*GR?)')
    df_sap['Gramaje'] = df_sap['Gramaje'].str.replace(r'[\.\s-]|GR?', '', regex=True, flags=re.IGNORECASE)
    df_sap['Gramaje'] = df_sap['Gramaje'] + 'GR'
    patron_tipo = r'(FLOW\w*|4PRO|5PRO|DOYPACK|COJIN|SACHET)'
    
    df_sap['Tipo'] = df_sap['ItemName'].str.extract(patron_tipo, expand=False)
    df_sap['Tipo'] = df_sap['Tipo'].str.replace(r'FLOW\w*', 'FLOWPACK', regex=True)
    
    df_sap['Resto'] = df_sap['ItemName']
    df_sap['Resto'] = df_sap['Resto'].str.replace(r'([\d\.,-]+\s*GR?)', '', regex=True)
    df_sap['Resto'] = df_sap['Resto'].str.replace(patron_tipo + '|PACK', '', regex=True)
    df_sap['Resto'] = df_sap['Resto'].str.replace('+', '', regex=False)
    df_sap['Resto'] = df_sap['Resto'].str.strip().str.replace(r'\s+', ' ', regex=True)
    
    mascara_stock = df_sap['StockEnBodega'] > 0
    gramajes_validos = r'(2500|2000|1000|500|340|250|125|70|50)G?'
    
    patron_estandar = f'{gramajes_validos}(4P|5P|DOY|FL|FLO)'
    mascara_estandar = df_sap['ItemCode'].str.contains(patron_estandar, regex=True, na=False)
    mascara_cojin = df_sap['ItemCode'].str.contains('COJIN', regex=False, na=False)
    mascara_nomenclatura = mascara_estandar | mascara_cojin
    
    df_sap = df_sap[mascara_stock & mascara_nomenclatura]
    
    df_sap = extraer_atributos_precio(df_sap) 
    df_sap = aplicar_pricing(df_sap)

    patron_purga = r'(MATE|BRILLANTE|BRILL|PAPEL|KRAFT|DELGADA|GRUESA|SIN\s+ZIPP?ER|CON\s+ZIPP?ER|ZIPP?ER|KIT\s+VAL|PEEL|VALVULA)'
    df_sap['Resto'] = df_sap['Resto'].str.replace(patron_purga, '', regex=True, flags=re.IGNORECASE)
    df_sap['Resto'] = df_sap['Resto'].str.strip().str.replace(r'\s+', ' ', regex=True)

    def limpiar_medidas_quirurgico(txt):
        if not txt: return txt
        txt = re.sub(r'(\d),(\d)', r'\1.\2', txt)
        txt = txt.replace('*', 'X')
        txt = re.sub(r'(\d)\s*[xX]\s*(\d)', r'\1X\2', txt)
        txt = re.sub(r'(\d+\.?\d*)X(\d+\.?\d*)X(\d+\.?\d*)', r'\1X\2 - \3', txt)
        return txt

    df_sap['Resto'] = df_sap['Resto'].apply(limpiar_medidas_quirurgico)

    colores_base = sorted(CATALOGO_COLORES.keys(), key=len, reverse=True)
    patron_color = r'(' + '|'.join([re.escape(c) for c in colores_base]) + r')'

    df_sap['Coincidencia_Color'] = df_sap['Resto'].str.extract(patron_color, expand=False).fillna('NO_IDENTIFICADO')

    def purgar_color(texto, color):
        if color == 'NO_IDENTIFICADO': return texto
        return str(texto).replace(color, '', 1)

    df_sap['Caracteristicas_Adicionales'] = df_sap.apply(lambda row: purgar_color(row['Resto'], row['Coincidencia_Color']), axis=1)

    df_sap['Bodega'] = df_sap['Bodega'].astype(str).str.strip().str.upper()
    
    codigos_carvajal = ['B011', 'B051', 'B054', 'B057', 'B060', 'B063', 'B066', 'B069', 'B072', 'B172', 'B176']
    codigos_norte = ['B012', 'B052', 'B055', 'B058', 'B061', 'B064', 'B067', 'B070', 'B073', 'B173', 'B175']

    condiciones = [df_sap['Bodega'].isin(codigos_carvajal), df_sap['Bodega'].isin(codigos_norte)]
    resultados = ['Carvajal', 'Norte']
    df_sap['sede de bodega'] = np.select(condiciones, resultados, default='tecplas')
    
    df_sap['Caracteristicas_Adicionales'] = df_sap['Caracteristicas_Adicionales'].str.replace(r'DELGADO', '', regex=True)
    df_sap['Caracteristicas_Adicionales'] = df_sap['Caracteristicas_Adicionales'].str.replace(r'\s+', ' ', regex=True).str.strip()
    df_sap['Caracteristicas_Adicionales'] = df_sap['Caracteristicas_Adicionales'].replace('', 'NINGUNO')
    
    df_sap['Bodega'] = df_sap['Bodega'].astype(str).str.strip().str.upper()
    df_sap['ItemCode'] = df_sap['ItemCode'].astype(str).str.strip().str.upper()
    df_sap['ItemCode_Sede'] = df_sap['ItemCode'] + '-' + df_sap['Bodega']
    
    df_sap = df_sap.where(pd.notnull(df_sap), None)
    return df_sap

# ==========================================
# 3. MÓDULO DE CARGA/EXPORTACIÓN (LOAD)
# ==========================================
def exportar_csv_auditoria(df: pd.DataFrame, ruta_salida: str):
    """
    Exporta el DataFrame a CSV y genera Excels individuales por tipo de producto,
    manteniendo la integridad de las rutas absolutas.
    """
    # 1. Guardar el CSV maestro (Usa la ruta absoluta directamente)
    df.to_csv(ruta_salida, index=False, encoding='utf-8-sig')

    # --- CONFIGURACIÓN DE EXPORTACIÓN ---
    mapeo_nombres = {
        "ItemCode": "SKU", "ItemName": "Descripción", "Gramaje": "capacidad en (gr)",
        "Tipo": "Categoría", "Coincidencia_Color": "Color", "SLength1": "Largo",
        "SWidth1": "Ancho", "SHeight1": "Alto", "SVolume": "Volumen Total"
    }
    
    columnas_esquema = [
        "ItemCode", "ItemName", "Gramaje", "Tipo","Coincidencia_Color", 
        "Caracteristicas_Adicionales", "Precio", "Unidades_Minimas",  
        "StockEnBodega", "SLength1", "SWidth1", "SHeight1", "SVolume"
    ]
    
    # --- PROCESAMIENTO DE RUTAS ---
    # Extraemos la carpeta donde debe vivir el archivo
    directorio = os.path.dirname(ruta_salida)
    # Extraemos solo el nombre del archivo sin la extensión .csv
    nombre_archivo_base = os.path.basename(ruta_salida).replace('.csv', '')
    
    total_verificacion = 0
    tipos_productos = df['Tipo'].unique()

    for tipo in tipos_productos:
        # Filtrado de datos por tipo
        df_tipo = df[df['Tipo'] == tipo].copy()
        columnas_existentes = [col for col in columnas_esquema if col in df_tipo.columns]
        df_final = df_tipo[columnas_existentes].copy()
        
        if "Precio" in df_final.columns:
            df_final = df_final[df_final["Precio"] != 0]
            
        df_final.rename(columns=mapeo_nombres, inplace=True)

        # 2. CONSTRUCCIÓN DE LA RUTA DEL EXCEL (EL ARREGLO)
        # Creamos el nombre del fichero: ej. "4PRO_Listado_generico_SAP_.xlsx"
        nombre_fichero_excel = f"{tipo}_{nombre_archivo_base}.xlsx"
        # Unimos el directorio original con el nuevo nombre
        ruta_archivo_excel = os.path.join(directorio, nombre_fichero_excel)
        
        # 3. GENERACIÓN DEL EXCEL CON TABLA
        with pd.ExcelWriter(ruta_archivo_excel, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, sheet_name='Auditoria', index=False)
            workbook  = writer.book
            worksheet = writer.sheets['Auditoria']
            
            (max_row, max_col) = df_final.shape
            column_settings = [{'header': column} for column in df_final.columns]
            
            worksheet.add_table(0, 0, max_row, max_col - 1, {
                'columns': column_settings,
                'style': 'TableStyleMedium9'
            })

        total_verificacion += len(df_final)
        registrar_evento(f"[OK] ¡Fusión completada! Excel con Tabla creado: {ruta_archivo_excel} ({len(df_final)} filas)")

# ==========================================
# ORQUESTADOR (MAIN)
# ==========================================
if __name__ == "__main__":
    
    sap_connector = SAPServiceLayerV2()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    registrar_evento("\n[INFO] ¡Hola, soy Goku! Iniciando el Torneo del Poder (Pipeline ETL Automatizado)...")
    
    if sap_connector.conectar():
        registrar_evento("[INFO] ¡Elevando el ki! Extrayendo datos en vivo desde el planeta Namekusei (HANA)...")
        df_crudo = sap_connector.extraer_datos_stock()
    else:
        registrar_evento("[CRITICAL] ¡Gokuuuuu! ¡Kriliiii! Abortando el torneo por fallo en conexión SAP.")
        exit(1)
    
    ARCHIVO_SALIDA = os.path.join(BASE_DIR, 'Listado_generico_SAP_.csv')

    registrar_evento("[INFO] ¡Transformación Super Saiyajin! Iniciando limpieza de datos...")
    df_limpio = transformar_datos(df_crudo)
    
    registrar_evento("\n=== EL RASTREADOR INDICA ESTA VISTA PREVIA ===")
    columnas_revision = ['ItemCode', 'ItemName','Gramaje', 'Tipo', 'Resto', 'Coincidencia_Color', 'Caracteristicas_Adicionales']
    # Mantengo el print aquí porque no es un evento de auditoría, es solo una tabla visual en consola
    print(df_limpio[columnas_revision].head(10).to_string(index=False))
    
    registrar_evento("\n[INFO] Creando cápsulas Hoi-Poi (Archivos de Auditoría)...")
    
    exportar_csv_auditoria(df_limpio, ARCHIVO_SALIDA)

    # ══════════════════════════════════════════════════════
    # SUBIR CSV A CPANEL (stock en tiempo real para la web)
    # ══════════════════════════════════════════════════════
    from subir_stock_ftp import subir_csv 
    subir_csv()
    
    integrador = EscalaIntegrator(df_limpio)
    integrador.ejecutar_ciclo()
    
    registrar_evento("\n[INFO] ¡Despertando al dragón Shenlong! (Centinela del Motor RAG)...")

    agente_rag = EscalaKnowledgeBaseAgent(ruta_base_archivos=ARCHIVO_SALIDA)
    agente_rag.evaluar_y_sincronizar()
    
    registrar_evento("[INFO] ¡El universo ha sido salvado! Pipeline ETL Global finalizado con éxito.")