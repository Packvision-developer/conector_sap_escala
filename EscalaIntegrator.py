import os
import requests
import pandas as pd
from dotenv import load_dotenv
from logger_escala import registrar_evento

load_dotenv()

class EscalaIntegrator:
    def __init__(self, df_actual: pd.DataFrame):
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.df_actual = df_actual
        self.archivo_memoria = os.path.join(BASE_DIR, 'memoria_escala_stock.csv')
        self.api_key = os.getenv('ESCALA_API_KEY')
        self.base_url = "https://public-api.escala.com/v1/pms/products"
        self.headers = {
            "x-api-key": f"{self.api_key}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)   

    def _pulse_check(self) -> bool:
        registrar_evento("\n[PASO 1] Concentrando Ki... ¡Rastreando la energía de Escala!")
        try:
            response = self.session.get(f"{self.base_url}?page=0&size=1", timeout=10)
            response.raise_for_status()
            total_en_escala = response.json().get('total', 0)
            registrar_evento(f" -> ¡El rastreador indica un nivel de pelea de {total_en_escala} productos activos!")
            if total_en_escala == 0 and os.path.exists(self.archivo_memoria):
                registrar_evento(" [ALERTA CRÍTICA] ¡Gokuuuuu! ¡Escala está vacía pero la memoria sigue aquí! ¡Alguien usó las esferas del dragón para borrar el inventario!")
                os.remove(self.archivo_memoria)
                return False
            return True
        except Exception as e:
            registrar_evento(f" [ERROR] ¡Maldición, Freezer! Falló el rastreo de Ki: {e}")
            return True

# ------------------------nuevo codigo---------------------------
    # FASE 1: EL RADAR GLOBAL (Reemplaza a _sanar_memoria)
    # Descargamos todo el catálogo real de Escala para no depender a ciegas del CSV
    def _escanear_escala_global(self):
        registrar_evento("\n[RADAR GLOBAL] ¡Activando el Ojo de Kami-Sama! Escaneando todo el universo de Escala...")
        pagina = 0
        tamaño_pagina = 100
        mapa_escala = {}
        try:
            while True:
                res = self.session.get(f"{self.base_url}?page={pagina}&size={tamaño_pagina}", timeout=15)
                res.raise_for_status()
                datos = res.json()
                items = datos.get('items', [])
                if not items:
                    break
                for item in items:
                    sku = item.get('sku')
                    uuid = item.get('id')
                    if sku and uuid:
                        mapa_escala[sku] = uuid
                registrar_evento(f" -> Página {pagina + 1} asimilada ({len(items)} guerreros)...")
                pagina += 1
                
            registrar_evento(f" -> [ÉXITO] Radar completo: {len(mapa_escala)} productos existen realmente en Escala.")
            return mapa_escala, True # Retorna el mapa y bandera de éxito
        except Exception as e:
            registrar_evento(f" [FATAL] ¡Cell destruyó la antena del Radar Global!: {e}")
            return {}, False
# ----------------fin de implementación------------------------------------

    def _cargar_memoria(self) -> pd.DataFrame:
        if os.path.exists(self.archivo_memoria):
            try:
                df_memoria = pd.read_csv(self.archivo_memoria, dtype=str)
                df_memoria['StockEnBodega'] = pd.to_numeric(df_memoria['StockEnBodega'], errors='coerce')
                registrar_evento(f" -> Memoria recuperada: {len(df_memoria)} registros encontrados en las ruinas del planeta Namekusei.")
                return df_memoria
            except Exception as e:
                registrar_evento(f" [ERROR] ¡Insecto! Archivo corrupto: {e}. Iniciaremos desde cero.")
                return pd.DataFrame()
        else:
            registrar_evento(" -> No hay memoria local. ¡El Tribunal juzgará todo desde cero!")
            return pd.DataFrame()

# ------------------------nuevo codigo---------------------------
    # FASE 2: EL TRIBUNAL DE ZENO-SAMA (Reemplaza al _calcular_delta antiguo)
    def _calcular_delta_dios(self, df_viejo: pd.DataFrame, radar_global: dict):
        registrar_evento("\n[PASO 3] El Tribunal de Zeno-Sama: Cruzando mundos (SAP vs Radar Global Escala)...")
        
        actual = self.df_actual.set_index('ItemCode_Sede')
        viejo = df_viejo.set_index('ItemCode_Sede') if not df_viejo.empty else pd.DataFrame()

        skus_sap = set(actual.index)
        skus_escala = set(radar_global.keys())

        # 1. NUEVOS: Están en SAP, pero no existen en el universo de Escala
        nuevos_idx = skus_sap - skus_escala
        df_nuevos = actual.loc[list(nuevos_idx)].reset_index()

        # 2. OBSOLETOS (FANTASMAS): Existen en Escala, pero SAP ya no los tiene
        obsoletos_idx = skus_escala - skus_sap
        # Se arma un DataFrame con los obsoletos y sus UUIDs directos del radar
        lista_obsoletos = [{'ItemCode_Sede': sku, 'escala_uuid': radar_global[sku]} for sku in obsoletos_idx]
        df_obsoletos = pd.DataFrame(lista_obsoletos) if lista_obsoletos else pd.DataFrame()

        # 3. MUTADOS: Existen en SAP y en Escala. Usamos el CSV solo para ver si cambió el stock numérico
        df_mutados = pd.DataFrame()
        if not viejo.empty:
            comunes_idx = actual.index.intersection(viejo.index)
            actual_comunes = actual.loc[comunes_idx]
            viejo_comunes = viejo.loc[comunes_idx]
            mascara_cambios = actual_comunes['StockEnBodega'] != viejo_comunes['StockEnBodega']
            df_mutados = actual_comunes[mascara_cambios].reset_index()
        else:
            # Si se perdió el CSV local, por precaución mutamos todos los que no son nuevos
            comunes_idx = skus_sap.intersection(skus_escala)
            df_mutados = actual.loc[list(comunes_idx)].reset_index()

        registrar_evento(f" -> ¡Veredicto! {len(df_nuevos)} Nuevos, {len(df_mutados)} Mutados, {len(df_obsoletos)} Obsoletos (Fantasmas a destruir).")
        return df_nuevos, df_mutados, df_obsoletos
# ----------------fin de implementación------------------------------------

    def _construir_payload(self, fila: pd.Series) -> dict:
        payload = {
            "name": str(fila.get('ItemName', 'Sin Nombre'))[:255],
            "sku": str(fila.get('ItemCode_Sede'))[:40],
            "price": float(fila.get('Precio', 0)),
            "isDigital": False,
            "currency": "COP",
            "custom": {}
        }

        def _inyectar_custom(uuid_key: str, valor, es_numerico=False):
            if pd.isna(valor) or valor is None or str(valor).strip() == "":
                return
            if es_numerico:
                try:
                    payload["custom"][uuid_key] = float(valor)
                except ValueError:
                    pass
            else:
                payload["custom"][uuid_key] = str(valor).strip()

        _inyectar_custom("cf_product_codigo_de_producto_cvvt_text", fila.get('ItemCode'))
        _inyectar_custom("cf_product_descripcion_sap_uacg_text", fila.get('ItemName'))
        _inyectar_custom("cf_product_gramaje_fsis_text", fila.get('Gramaje'))
        _inyectar_custom("cf_product_tipo_de_empaque_dyfo_text", fila.get('Tipo'))
        _inyectar_custom("cf_product_color_nkfe_text", fila.get('Coincidencia_Color'))
        _inyectar_custom("cf_product_caracteristicas_adicionales_oxhp_text", fila.get('Caracteristicas_Adicionales'))
        _inyectar_custom("cf_product_longitud_nakq_decimal", fila.get('SLength1'), es_numerico=True)
        _inyectar_custom("cf_product_ancho_cwtk_decimal", fila.get('SWidth1'), es_numerico=True)
        _inyectar_custom("cf_product_altura_sogj_decimal", fila.get('SHeight1'), es_numerico=True)
        _inyectar_custom("cf_product_volumen_izmc_decimal", fila.get('SVolume'), es_numerico=True)
        _inyectar_custom("cf_product_bodega_tcat_text", fila.get('Bodega'))
        _inyectar_custom("cf_product_sede_fisica_gpgw_text", fila.get('sede de bodega'))
        _inyectar_custom("cf_product_cantidad_en_stock_rafu_decimal", fila.get('StockEnBodega'), es_numerico=True)
        _inyectar_custom("cf_product_cantidad_minima_de_venta_generico_iuvf_number", fila.get('Unidades_Minimas'), es_numerico=True)
        
        if not payload["custom"]:
            del payload["custom"]

        return payload

    def _peticion_resiliente(self, verbo: str, url: str, payload: dict = None, max_intentos=3):
        import time
        ultimo_error = "Ninguno"
        for intento in range(1, max_intentos + 1):
            try:
# ------------------------nuevo codigo---------------------------
                # Se incorpora el método DELETE
                if verbo.upper() == "POST":
                    res = self.session.post(url, json=payload, timeout=5)
                elif verbo.upper() == "PUT":
                    res = self.session.put(url, json=payload, timeout=5)
                elif verbo.upper() == "DELETE":
                    res = self.session.delete(url, timeout=5) # El Hakai no lleva body
                else:
                    return None
# ----------------fin de implementación------------------------------------
                
                if res.status_code in (200, 201, 204):
                    return res

                ultimo_error = f"HTTP {res.status_code} - {res.text}"
                if res.status_code in [500, 502, 503, 504, 429]:
                    registrar_evento(f" [REINTENTO {intento}/{max_intentos}] ¡Escala está usando la técnica de la teletransportación! (HTTP {res.status_code}). Respirando...")
                    time.sleep(0.5)
                    continue
                else:
                    registrar_evento(f" [ERROR FATAL] ¡Escala rechazó el ataque! {ultimo_error}")
                    return res

            except requests.exceptions.Timeout:
                ultimo_error = "Timeout (Escala no respondió en 10 segundos)"
                registrar_evento(f" [REINTENTO {intento}/{max_intentos}] Tiempo agotado. Escala está reuniendo energía...")
                time.sleep(1)
            except requests.exceptions.RequestException as e:
                ultimo_error = f"Error de Conexión: {str(e)}"
                registrar_evento(f" [REINTENTO {intento}/{max_intentos}] ¡Fallo de red! Se rompió el puente de la serpiente.")
                time.sleep(1)

        registrar_evento(f" [FALLO CRÍTICO] Se agotaron los {max_intentos} intentos. ¡Goku, explota Krilin! (Producto saltado).")
        return None

    def _ejecutar_contingencia_put(self, sku: str, payload: dict):
        try:
            res = self.session.get(f"{self.base_url}?sku={sku}", timeout=10)
            if res.status_code == 200 and res.json().get('total', 0) > 0:
                nuevo_id = res.json()['items'][0]['id']
                put_res = self.session.put(f"{self.base_url}/{nuevo_id}", json=payload)
                return put_res.status_code == 200, nuevo_id
            else:
                post_res = self.session.post(self.base_url, json=payload)
                if post_res.status_code in (201, 200):
                    return True, post_res.json().get('id')
                return False, None
        except Exception as e:
            return False, None

# ------------------------nuevo codigo---------------------------
    # FASE 3: LA COLA DE COMBATE (Se añaden obsoletos y el radar global)
    def _ejecutar_cola(self, df_nuevos, df_mutados, df_obsoletos, radar_global):
# ----------------fin de implementación------------------------------------
        import time
        registrar_evento("\n[PASO 4] ¡Elevando el Ki al máximo! Ejecutando Operaciones HTTP...")
        
# ------------------------nuevo codigo---------------------------
        # CURA DE AMNESIA: Inicializamos el mapa final con TODOS los UUIDs del Radar
        mapa_uuids_final = radar_global.copy()
# ----------------fin de implementación------------------------------------

        for _, fila in df_nuevos.iterrows():
            sku = fila['ItemCode_Sede']
            payload = self._construir_payload(fila)
            registrar_evento(f" -> [POST] ¡Kame Hame Haaaa! Creando a {sku}...")
            res = self._peticion_resiliente("POST", self.base_url, payload)
            if res and res.status_code in (201, 200):
# ------------------------nuevo codigo---------------------------
                mapa_uuids_final[sku] = res.json().get('id') # Añadir nuevo al mapa final
# ----------------fin de implementación------------------------------------
            else:
                texto_error = res.text if res else "Error de conexión o Timeout tras reintentos"
                codigo_http = res.status_code if res else "N/A"
                registrar_evento(f" [ERROR POST] ¡El ataque a {sku} falló! (Status: {codigo_http}): {texto_error}")

        for _, fila in df_mutados.iterrows():
            sku = fila['ItemCode_Sede']
# ------------------------nuevo codigo---------------------------
            # Buscamos su UUID en el radar global directamente
            uuid_escala = mapa_uuids_final.get(sku)
# ----------------fin de implementación------------------------------------
            payload = self._construir_payload(fila)
            registrar_evento(f" -> [PUT] ¡Transformación Super Saiyajin! Actualizando {sku} (Nuevo nivel de poder: {fila['StockEnBodega']})...")
            
            if not uuid_escala or pd.isna(uuid_escala):
                exito, nuevo_uuid = self._ejecutar_contingencia_put(sku, payload)
                if exito: mapa_uuids_final[sku] = nuevo_uuid
            else:
                res = self._peticion_resiliente("PUT", f"{self.base_url}/{uuid_escala}", payload)
                if res and res.status_code == 200:
                    mapa_uuids_final[sku] = uuid_escala
                else:
                    registrar_evento(f" [INFO] ¡El PUT fue bloqueado! Activando radar de las esferas del dragón para buscar a {sku}...")
                    exito, nuevo_uuid = self._ejecutar_contingencia_put(sku, payload)
                    if exito: mapa_uuids_final[sku] = nuevo_uuid
            time.sleep(0.25)

# ------------------------nuevo codigo---------------------------
        # EL HAKAI (ELIMINAR OBSOLETOS)
        if not df_obsoletos.empty:
            registrar_evento(f"\n -> [DELETE] ¡Detectados {len(df_obsoletos)} intrusos! Preparando la técnica del Hakai...")
            for _, fila in df_obsoletos.iterrows():
                sku = fila['ItemCode_Sede']
                uuid_escala = fila['escala_uuid'] # Lo sacamos del df_obsoletos

                if uuid_escala and not pd.isna(uuid_escala):
                    registrar_evento(f" -> [DELETE] Borrando {sku} del universo de Escala...")
                    res = self._peticion_resiliente("DELETE", f"{self.base_url}/{uuid_escala}")
                    
                    if res and res.status_code in (200, 204):
                        registrar_evento(f" [ÉXITO] {sku} ha sido desintegrado.")
                        # IMPORTANTE: Remover de la memoria para que no se guarde en CSV
                        if sku in mapa_uuids_final:
                            del mapa_uuids_final[sku] 
                    else:
                        texto_error = res.text if res else "Error desconocido"
                        registrar_evento(f" [FALLO] {sku} resistió el Hakai: {texto_error}")
                
                time.sleep(0.2)

        # Devolvemos el mapa perfecto (Radar Original + Nuevos Creados - Obsoletos Borrados)
        return mapa_uuids_final
# ----------------fin de implementación------------------------------------

    def _guardar_memoria(self, uuids_obtenidos: dict):
        registrar_evento("\n[PASO 5] ¡Sellando el poder con la técnica del Mafuba! Persistiendo en memoria local...")
        df_final = self.df_actual.copy()
        df_final['escala_uuid'] = df_final['ItemCode_Sede'].map(uuids_obtenidos)
        df_final.to_csv(self.archivo_memoria, index=False)
        registrar_evento(f" -> ¡Memoria guardada! {len(df_final)} registros asegurados para la próxima batalla.")

    def ejecutar_ciclo(self):
        registrar_evento("\n==================================================")
        registrar_evento("¡INICIANDO TORNEO DE LAS ARTES MARCIALES! (INTEGRADOR ESCALA)")
        registrar_evento("==================================================")

        self._pulse_check()
        df_viejo = self._cargar_memoria()
        
# ------------------------nuevo codigo---------------------------
        # NUEVO FLUJO MAESTRO DE SINCRONIZACIÓN
        # 1. Obtenemos la verdad absoluta de la nube
        radar_global, radar_exitoso = self._escanear_escala_global()
        
        # Red de seguridad: si el radar falla por red, no hacemos destrozos
        if not radar_exitoso:
            registrar_evento("\n[FATAL] El Radar Global falló. Abortando torneo para evitar destruir el universo por error.")
            return

        # 2. El Tribunal compara SAP vs Nube (y usa el CSV solo para los mutados)
        df_nuevos, df_mutados, df_obsoletos = self._calcular_delta_dios(df_viejo, radar_global)

        if df_nuevos.empty and df_mutados.empty and df_obsoletos.empty:
            registrar_evento("\n[INFO] ¡El universo está en paz! No hay cambios en el inventario. Se cancela el ataque.")
            # Aunque no haya cambios de stock, si la memoria local se había borrado, la reconstruimos sana
            if df_viejo.empty:
                self._guardar_memoria(radar_global)
            return

        # 3. La batalla
        diccionario_uuids = self._ejecutar_cola(df_nuevos, df_mutados, df_obsoletos, radar_global)
# ----------------fin de implementación------------------------------------

        if diccionario_uuids:
            self._guardar_memoria(diccionario_uuids)
            registrar_evento("\n[INFO] ¡Sincronización finalizada! Siempre te recordaré, Majin Buu...")

                  # ══════════════════════════════════════════════════════
        # PASO FINAL: Subir CSV actualizado a cPanel (web)
        # ══════════════════════════════════════════════════════
        try:
            from subir_stock_ftp import subir_csv
            registrar_evento("\n[WEB] ¡Transmitiendo el poder al servidor web! Subiendo stock a cPanel...")
            exito = subir_csv()
            if exito:
                registrar_evento(" -> [WEB] ✅ ¡Stock actualizado en la página web exitosamente!")
            else:
                registrar_evento(" -> [WEB] ⚠️ No se pudo subir el CSV al servidor web.")
        except Exception as e:
            registrar_evento(f" -> [WEB] ❌ Error al subir CSV: {e}")
