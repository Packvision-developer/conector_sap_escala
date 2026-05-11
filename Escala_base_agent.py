import os
import time
import json
import hashlib
import requests
from pycognito import Cognito
from dotenv import load_dotenv
from logger_escala import registrar_evento

load_dotenv() 

class EscalaKnowledgeBaseAgent:
    def __init__(self, ruta_base_archivos: str):
        RAG_DIR = os.path.dirname(os.path.abspath(__file__))
        # --- CREDENCIALES ---
        self.USER_POOL_ID = os.getenv('AWS_USER_POOL_ID')
        self.CLIENT_ID = os.getenv('AWS_CLIENT_ID')
        self.USERNAME = os.getenv('AWS_USERNAME')
        self.PASSWORD = os.getenv('AWS_PASSWORD')
        self.REFRESH_TOKEN_FALLBACK = os.getenv('TOKEN_FALLBACK')

        # --- ESTADO Y MAPEO ---
        self.archivo_estado = os.path.join(RAG_DIR, "estado_rag.json")
        self.tiempo_cooldown = 7200 
        self.token_activo = None
        self.ruta_base = ruta_base_archivos.replace('.csv', '') 
        
        self.headers_api = {
            'accept': 'application/json, text/plain, */*',
            'origin': 'https://app.escala.com',
            'referer': 'https://app.escala.com/'
        }

        self.mapa_rutas = {
            "4PRO": "Producto 4pro Generico",
            "5PRO": "Producto 5pro Generico",
            "FLOWPACK": "Producto Flowpack generico",
            "DOYPACK": "Producto Doypack generico"
        }

    def _calcular_md5(self, ruta_archivo: str) -> str:
        if not os.path.exists(ruta_archivo): return None
        hash_md5 = hashlib.md5()
        with open(ruta_archivo, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _autenticar_hibrido(self) -> bool:
        registrar_evento("\n[AUTH] ¡Buscando las esferas del dragón! Negociando llaves con AWS Cognito...")
        
        try:
            registrar_evento("   -> [INTENTO 1] ¡Kaio-ken! Ejecutando rutinas matemáticas SRP (pycognito)...")
            u = Cognito(self.USER_POOL_ID, self.CLIENT_ID, username=self.USERNAME)
            u.authenticate(password=self.PASSWORD)
            self.token_activo = u.id_token
            self.headers_api['authorization'] = self.token_activo
            registrar_evento("   -> [ÉXITO] ¡Poder al máximo! Pycognito rompió la bóveda. Sesión iniciada.")
            return True
        except Exception as e:
            registrar_evento(f"   -> [FALLO SRP] ¡Maldición, perdí mi transformación! Pycognito se estrelló: {e}")
        
        registrar_evento("   -> [INTENTO 2] ¡Técnica de la teletransportación! Activando contingencia: Refresh Token auth_flow...")
        try:
            url_cognito = "https://cognito-idp.us-east-1.amazonaws.com/"
            headers_cogn = {"Content-Type": "application/x-amz-json-1.1", "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"}
            payload_cogn = {
                "ClientId": self.CLIENT_ID,
                "AuthFlow": "REFRESH_TOKEN_AUTH",
                "AuthParameters": {"REFRESH_TOKEN": self.REFRESH_TOKEN_FALLBACK}
            }
            res = requests.post(url_cognito, headers=headers_cogn, json=payload_cogn)
            if res.status_code == 200:
                self.token_activo = res.json()["AuthenticationResult"]["IdToken"]
                self.headers_api['authorization'] = self.token_activo
                registrar_evento("   -> [ÉXITO] ¡El pase VIP funcionó! Contingencia superada.")
                return True
            else:
                registrar_evento(f"   -> [FATAL] ¡Krilin explotó de nuevo! La contingencia falló. AWS dice: {res.text}")
                return False
        except Exception as e:
            registrar_evento(f"   -> [FATAL RED] ¡El planeta Namekusei está a punto de explotar! Colapso al contactar AWS: {e}")
            return False

    def _obtener_repo_id(self, nombre_objetivo: str) -> str:
        url = "https://api.escala.com/app/rag-service/rag/repository"
        res = requests.get(url, headers=self.headers_api)
        if res.status_code == 200:
            for repo in res.json().get('data', []):
                if repo.get('name') == nombre_objetivo: return repo.get('id')
        return None

    def _buscar_documentos_fantasma(self, repo_id: str, prefijo: str) -> list:
            # Ya no usamos regex estrictos. Buscamos cualquier archivo que empiece con el prefijo (ej. "5PRO")
            url = f"https://api.escala.com/app/rag-service/document/document?repository_id={repo_id}&size=50"
            res = requests.get(url, headers=self.headers_api)
            
            ids_fantasmas = []
            if res.status_code == 200:
                for doc in res.json().get('data', []):
                    nombre_servidor = doc.get('file_name', '')
                    
                    # Si el archivo empieza con el prefijo (ej. "5PRO_"), lo marcamos para destrucción
                    if nombre_servidor.startswith(f"{prefijo}_"):
                        registrar_evento(f"   -> [RADAR] ¡Encontré un posible fantasma! Alias: '{nombre_servidor}' (ID: {doc.get('id')})")
                        ids_fantasmas.append(doc.get('id'))
                        
            return ids_fantasmas

    def _subir_s3(self, file_path: str, mime_type: str) -> tuple:
        file_size = os.path.getsize(file_path)
        r1 = requests.get("https://api.escala.com/app/file-storage/nodes/get_upload_url", headers=self.headers_api)
        r1.raise_for_status()
        
        post_url, read_url = r1.json().get('post_url'), r1.json().get('read_url')
        
        headers_s3 = {'Content-Type': mime_type, 'Origin': 'https://app.escala.com', 'Referer': 'https://app.escala.com/'}
        with open(file_path, 'rb') as f:
            r2 = requests.put(post_url, data=f.read(), headers=headers_s3)
            r2.raise_for_status()
        return read_url, file_size

 # ------------------------nuevo codigo---------------------------
    def evaluar_y_sincronizar(self, force_sync: bool = False):
        registrar_evento("\n========================================================")
        registrar_evento(" AUDITORÍA DE CONOCIMIENTO RAG (EL OJO DE KAMI-SAMA)")
        registrar_evento("========================================================")
        
        estado = {"timestamp": 0, "hashes": {}}
        if os.path.exists(self.archivo_estado):
            try:
                with open(self.archivo_estado, 'r') as f: estado = json.load(f)
            except: pass

        tiempo_actual = int(time.time())
        segundos_pasados = tiempo_actual - estado["timestamp"]
        
        if segundos_pasados < self.tiempo_cooldown and not force_sync:
            faltan = (self.tiempo_cooldown - segundos_pasados) // 60
            registrar_evento(f"[CENTINELA] ¡Entrenamiento en la gravedad aumentada! Faltan {faltan} minutos para la próxima ventana RAG. Abortando.")
            return

        registrar_evento("[CENTINELA] ¡Ventana abierta! Preparando validación cruzada (Local vs Nube)...")

        # 1. AUTENTICACIÓN TEMPRANA (Necesaria para escanear los repositorios de Escala)
        if not self._autenticar_hibrido():
            registrar_evento("[FATAL] Sin autenticación no podemos usar el Radar. Abortando misión.")
            return

        archivos_modificados = {}
        mime_excel = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        base_rag_url = "https://api.escala.com/app/rag-service/document/document"

        # 2. ARREGLO DEL BUG DE RUTAS (Evita que intente buscar "5PRO_/home/...")
        directorio_base = os.path.dirname(self.ruta_base)
        nombre_base = os.path.basename(self.ruta_base)

        for tipo in self.mapa_rutas.keys():
            # Construcción segura de la ruta física del archivo
            if directorio_base:
                nombre_archivo = os.path.join(directorio_base, f"{tipo}_{nombre_base}.xlsx")
            else:
                nombre_archivo = f"{tipo}_{nombre_base}.xlsx"
            
            if not os.path.exists(nombre_archivo):
                registrar_evento(f"   [ALERTA] No encuentro el ki local de: {nombre_archivo}")
                continue
            
            # 3. CÁLCULO DE HASH LOCAL
            nuevo_hash = self._calcular_md5(nombre_archivo)
            hash_viejo = estado["hashes"].get(nombre_archivo)
            
            # 4. ESCANEO DEL REPOSITORIO EN LA NUBE (RADAR)
            repo_objetivo = self.mapa_rutas[tipo]
            repo_id = self._obtener_repo_id(repo_objetivo)
            
            if not repo_id:
                registrar_evento(f"   [ERROR] No se encontró el repositorio destino '{repo_objetivo}' en Escala.")
                continue

            ids_fantasmas = self._buscar_documentos_fantasma(repo_id, tipo)

            # 5. EL TRIBUNAL DE ZENO-SAMA DECIDE LA MUTACIÓN
            necesita_sincronizar = False
            razon = ""

            if force_sync:
                necesita_sincronizar = True
                razon = "Modo Dios (Sincronización Forzada Activada)"
            elif nuevo_hash != hash_viejo:
                necesita_sincronizar = True
                razon = f"Hash local modificado ({nuevo_hash[-6:]})"
            elif len(ids_fantasmas) == 0:
                necesita_sincronizar = True
                razon = "Repositorio en nube VACÍO (El archivo desapareció de Escala)"
            elif len(ids_fantasmas) > 1:
                necesita_sincronizar = True
                razon = f"Anomalía en la nube: {len(ids_fantasmas)} documentos fantasma/duplicados detectados"

            if necesita_sincronizar:
                registrar_evento(f"   -> [MUTACIÓN CONFIRMADA] ¡Iniciando protocolo para {tipo}! Motivo: {razon}")
                archivos_modificados[tipo] = {
                    "archivo": nombre_archivo, 
                    "hash": nuevo_hash,
                    "fantasmas_a_borrar": ids_fantasmas,
                    "repo_id": repo_id
                }
            else:
                registrar_evento(f"   -> [IGNORADO] {tipo} está sano localmente y con 1 solo archivo en la nube. ¡Perfecto!")

        # 6. LA BATALLA FINAL (Subida a S3 y Limpieza)
        if not archivos_modificados:
            registrar_evento("\n[INFO] ¡El universo está en paz! Ningún catálogo requiere intervención. Renovando timestamp y saliendo.")
            estado["timestamp"] = tiempo_actual
            with open(self.archivo_estado, 'w') as f: json.dump(estado, f)
            return

        for tipo, datos in archivos_modificados.items():
            archivo_local = datos["archivo"]
            repo_id = datos["repo_id"]
            ids_fantasmas = datos["fantasmas_a_borrar"]
            
            # Extraemos solo el nombre final del archivo para mandarlo bonito a la nube
            nombre_final_nube = os.path.basename(archivo_local)
            
            registrar_evento(f"\n[OPERACIÓN] ¡Inyectando el poder de {nombre_final_nube} -> Repo ID: {repo_id[-6:]}!")
            registrar_evento("   -> ¡Volando hacia la nube voladora! Negociando con S3 y subiendo binario...")
            
            try:
                read_url, size = self._subir_s3(archivo_local, mime_excel)
            except Exception as e:
                registrar_evento(f"   [ERROR S3] ¡Fallo la carga! Caímos de la torre de Karin: {e}")
                continue

            payload = {
                "url": read_url, "name": nombre_final_nube, "repository_id": repo_id,
                "metadata": {"name": nombre_final_nube, "size": size, "type": mime_excel}
            }

            try:
                # 6.1 HAKAI A TODOS LOS FANTASMAS (Limpieza absoluta)
                if ids_fantasmas:
                    registrar_evento(f"   -> ¡Limpiando el terreno! Ejecutando HAKAI (DELETE) sobre {len(ids_fantasmas)} documentos viejos...")
                    for fantasma_id in ids_fantasmas:
                        requests.delete(f"{base_rag_url}/{fantasma_id}", headers=self.headers_api)
                        time.sleep(0.5)
                        registrar_evento(f"      - Fantasma {fantasma_id} desintegrado.")

                # 6.2 CREAMOS EL NUEVO GUERRERO LIMPIO
                registrar_evento("   -> ¡Inyectando el nuevo código genético (POST)...")
                r_post = requests.post(f"{base_rag_url}/add", headers=self.headers_api, json=payload)
                r_post.raise_for_status()
                registrar_evento(f"   [ÉXITO] ¡Nuevo guerrero Z registrado! Documento índice creado: {r_post.json().get('entity', {}).get('id')}")
                
                estado["hashes"][archivo_local] = datos["hash"]
                
            except Exception as e:
                registrar_evento(f"   [FATAL API] ¡Gokuuuuuu! El motor RAG rechazó el ataque: {e}")

        registrar_evento("\n[PASO FINAL] ¡Sellando el poder en la vasija con el Mafuba! Persistiendo hashes y sellando ventana de tiempo...")
        estado["timestamp"] = tiempo_actual
        with open(self.archivo_estado, 'w') as f: json.dump(estado, f)
        registrar_evento("[INFO] ¡La saga de Majin Buu ha terminado! Operación RAG concluida.")
# ----------------fin de implementación------------------------------------