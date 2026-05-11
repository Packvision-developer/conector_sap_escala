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
        self.api_key = os.getenv('ESCAL_API_KEY')
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

    def _sanar_memoria(self, df_viejo: pd.DataFrame) -> pd.DataFrame:
        if 'escala_uuid' not in df_viejo.columns:
            df_viejo['escala_uuid'] = pd.NA

        mascara_fantasmas = df_viejo['escala_uuid'].isna() | (df_viejo['escala_uuid'].astype(str).str.strip() == "")
        fantasmas_count = mascara_fantasmas.sum()

        if fantasmas_count == 0:
            return df_viejo

        registrar_evento(f"\n[SEMILLA DEL ERMITAÑO] ¡Atención! Detectados {fantasmas_count} productos heridos sin UUID.")
        registrar_evento(" -> ¡Iniciando el ritual de la Habitación del Tiempo (Sincronización Paginada)...")

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
                    sku_servidor = item.get('sku')
                    id_servidor = item.get('id')
                    if sku_servidor and id_servidor:
                        mapa_escala[sku_servidor] = id_servidor
                registrar_evento(f" -> ¡Absorbiendo la energía de la página {pagina + 1} ({len(items)} items)... ¡Como Majin Buu!")
                pagina += 1

        except Exception as e:
            registrar_evento(f" [FATAL] ¡Cell nos ha interrumpido! Falló la curación: {e}")
            registrar_evento(" -> El sistema trabajará con amnesia temporal, ¡como Goku cuando se golpeó la cabeza de niño!")
            return df_viejo

        registrar_evento(f" -> Descarga completa. {len(mapa_escala)} IDs en el radar. ¡Toma mi energía!")
        df_viejo['escala_uuid'] = df_viejo['escala_uuid'].fillna(df_viejo['ItemCode_Sede'].map(mapa_escala))
        fantasmas_restantes = df_viejo['escala_uuid'].isna().sum()
        registrar_evento(f" [ÉXITO] ¡Fusión completada! Fantasmas irremediables restantes: {fantasmas_restantes}")
        df_viejo.to_csv(self.archivo_memoria, index=False)
        return df_viejo

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
            registrar_evento(" -> No hay memoria local. ¡Preparando un BIG BANG ATTACK (POST Masivo)!")
            return pd.DataFrame()

    def _calcular_delta(self, df_viejo: pd.DataFrame):
        registrar_evento("\n[PASO 3] Calculando el poder de pelea (Diferencias de Stock)...")
        if df_viejo.empty:
            return self.df_actual, pd.DataFrame(), pd.DataFrame()

        actual = self.df_actual.set_index('ItemCode_Sede')
        viejo = df_viejo.set_index('ItemCode_Sede')

        nuevos_idx = actual.index.difference(viejo.index)
        df_nuevos = actual.loc[nuevos_idx].reset_index()

        obsoletos_idx = viejo.index.difference(actual.index)
        df_obsoletos = viejo.loc[obsoletos_idx].reset_index()

        comunes_idx = actual.index.intersection(viejo.index)
        actual_comunes = actual.loc[comunes_idx]
        viejo_comunes = viejo.loc[comunes_idx]
        mascara_cambios = actual_comunes['StockEnBodega'] != viejo_comunes['StockEnBodega']
        df_mutados = actual_comunes[mascara_cambios].reset_index()

        registrar_evento(f" -> ¡El rastreador dice que hay {len(df_nuevos)} Nuevos guerreros y {len(df_mutados)} han mutado su poder!")
        return df_nuevos, df_mutados, df_obsoletos

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

    def _peticion_resiliente(self, verbo: str, url: str, payload: dict, max_intentos=3):
        import time
        ultimo_error = "Ninguno"
        for intento in range(1, max_intentos + 1):
            try:
                if verbo.upper() == "POST":
                    res = self.session.post(url, json=payload, timeout=5)
                elif verbo.upper() == "PUT":
                    res = self.session.put(url, json=payload, timeout=5)
                else:
                    return None
                
                if res.status_code in (200, 201):
                    return res

                ultimo_error = f"HTTP {res.status_code} - {res.text}"
                if res.status_code in [500, 502, 503, 504, 429]:
                    registrar_evento(f" [REINTENTO {intento}/{max_intentos}] ¡Escala está usando la técnica de la teletransportación! (HTTP {res.status_code}). Respirando...")
                    time.sleep(0.5)
                    continue
                else:
                    registrar_evento(f" [ERROR FATAL] ¡Escala rechazó el ataque! El JSON no es digno: {ultimo_error}")
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

    def _ejecutar_cola(self, df_nuevos, df_mutados, df_viejo_con_uuids):
        import time
        registrar_evento("\n[PASO 4] ¡Elevando el Ki al máximo! Ejecutando Operaciones HTTP...")
        nuevos_uuids = {}

        for _, fila in df_nuevos.iterrows():
            sku = fila['ItemCode_Sede']
            payload = self._construir_payload(fila)
            registrar_evento(f" -> [POST] ¡Kame Hame Haaaa! Creando a {sku}...")
            res = self._peticion_resiliente("POST", self.base_url, payload)
            if res and res.status_code in (201, 200):
                nuevos_uuids[sku] = res.json().get('id')
            else:
                texto_error = res.text if res else "Error de conexión o Timeout tras reintentos"
                codigo_http = res.status_code if res else "N/A"
                registrar_evento(f" [ERROR POST] ¡El ataque a {sku} falló! (Status: {codigo_http}): {texto_error}")

        mapa_uuids_viejos = {}
        if not df_viejo_con_uuids.empty and 'escala_uuid' in df_viejo_con_uuids.columns:
            mapa_uuids_viejos = df_viejo_con_uuids.set_index('ItemCode_Sede')['escala_uuid'].to_dict()

        for _, fila in df_mutados.iterrows():
            sku = fila['ItemCode_Sede']
            uuid_escala = mapa_uuids_viejos.get(sku)
            payload = self._construir_payload(fila)
            registrar_evento(f" -> [PUT] ¡Transformación Super Saiyajin! Actualizando {sku} (Nuevo nivel de poder: {fila['StockEnBodega']})...")
            
            if not uuid_escala or pd.isna(uuid_escala):
                exito, nuevo_uuid = self._ejecutar_contingencia_put(sku, payload)
                if exito: nuevos_uuids[sku] = nuevo_uuid
            else:
                res = self._peticion_resiliente("PUT", f"{self.base_url}/{uuid_escala}", payload)
                if res and res.status_code == 200:
                    nuevos_uuids[sku] = uuid_escala
                else:
                    registrar_evento(f" [INFO] ¡El PUT fue bloqueado! Activando radar de las esferas del dragón para buscar a {sku}...")
                    exito, nuevo_uuid = self._ejecutar_contingencia_put(sku, payload)
                    if exito: nuevos_uuids[sku] = nuevo_uuid
            time.sleep(0.25)

        return nuevos_uuids

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
        
        # --- EL CAMBIO NIVEL DIOS ---
        if df_viejo.empty:
            registrar_evento("[!] Memoria ausente. Creando plantilla de emergencia desde SAP...")
            # Creamos un DataFrame con los códigos de SAP pero con UUIDs vacíos
            df_viejo = self.df_actual.copy()
            df_viejo['escala_uuid'] = pd.NA
        # ----------------------------

        df_viejo = self._sanar_memoria(df_viejo)
        df_nuevos, df_mutados, df_obsoletos = self._calcular_delta(df_viejo)

        if df_nuevos.empty and df_mutados.empty:
            registrar_evento("\n[INFO] ¡El universo está en paz! No hay cambios en el inventario. Se cancela el ataque.")
            return

        diccionario_uuids = self._ejecutar_cola(df_nuevos, df_mutados, df_viejo)
        if diccionario_uuids:
            self._guardar_memoria(diccionario_uuids)
            registrar_evento("\n[INFO] ¡Sincronización finalizada! Siempre te recordaré, Majin Buu...")