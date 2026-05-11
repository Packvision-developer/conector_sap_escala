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

    def _buscar_documento(self, repo_id: str, file_name: str) -> str:
        import re 
        
        url = f"https://api.escala.com/app/rag-service/document/document?repository_id={repo_id}&size=50"
        res = requests.get(url, headers=self.headers_api)
        
        if res.status_code == 200:
            nombre_raiz = file_name.replace('.xlsx', '')
            patron_seguro = rf"^{re.escape(nombre_raiz)}(\s*\(\d+\))?\.xlsx$"
            
            for doc in res.json().get('data', []):
                nombre_servidor = doc.get('file_name', '')
                
                if re.match(patron_seguro, nombre_servidor):
                    registrar_evento(f"   -> [RADAR] ¡Encontré tu Ki! Archivo homólogo encontrado en el servidor bajo el alias: '{nombre_servidor}'")
                    return doc.get('id')
                    
        return None

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

    def evaluar_y_sincronizar(self):
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
        
        if segundos_pasados < self.tiempo_cooldown:
            faltan = (self.tiempo_cooldown - segundos_pasados) // 60
            registrar_evento(f"[CENTINELA] ¡Entrenamiento en la gravedad aumentada! Faltan {faltan} minutos para la próxima ventana RAG. Abortando.")
            return

        registrar_evento("[CENTINELA] ¡Ventana de tiempo abierta! Evaluando el Ki de los archivos...")
        archivos_modificados = {}
        
        for tipo in self.mapa_rutas.keys():
            nombre_archivo = f"{tipo}_{self.ruta_base}.xlsx" 
            if not os.path.exists(nombre_archivo): continue
            
            nuevo_hash = self._calcular_md5(nombre_archivo)
            hash_viejo = estado["hashes"].get(nombre_archivo)
            
            if nuevo_hash != hash_viejo:
                registrar_evento(f"   -> [MUTACIÓN] ¡El nivel de pelea de {nombre_archivo} ha cambiado! (Hash: {nuevo_hash[-6:]}).")
                archivos_modificados[tipo] = {"archivo": nombre_archivo, "hash": nuevo_hash}
            else:
                registrar_evento(f"   -> [IGNORADO] {nombre_archivo} no ha entrenado lo suficiente. Es matemáticamente idéntico. Se omite.")

        if not archivos_modificados:
            registrar_evento("[INFO] ¡El universo está en paz! Ningún catálogo ha cambiado en las últimas 2 horas. Renovando timestamp y saliendo.")
            estado["timestamp"] = tiempo_actual
            with open(self.archivo_estado, 'w') as f: json.dump(estado, f)
            return

        if not self._autenticar_hibrido(): return

        mime_excel = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        base_rag_url = "https://api.escala.com/app/rag-service/document/document"

        for tipo, datos in archivos_modificados.items():
            archivo_local = datos["archivo"]
            repo_objetivo = self.mapa_rutas[tipo]
            
            registrar_evento(f"\n[OPERACIÓN] ¡Inyectando el poder de {archivo_local} -> [{repo_objetivo}]!")
            
            repo_id = self._obtener_repo_id(repo_objetivo)
            if not repo_id:
                registrar_evento(f"   [ERROR] ¡Vegeta, no encuentro su ki! No se encontró el repositorio destino. Saltando...")
                continue
                
            doc_id = self._buscar_documento(repo_id, archivo_local)
            
            registrar_evento("   -> ¡Volando hacia la nube voladora! Negociando con S3 y subiendo binario...")
            try:
                read_url, size = self._subir_s3(archivo_local, mime_excel)
            except Exception as e:
                registrar_evento(f"   [ERROR S3] ¡Fallo la carga! Caímos de la torre de Karin: {e}")
                continue

            payload = {
                "url": read_url, "name": archivo_local, "repository_id": repo_id,
                "metadata": {"name": archivo_local, "size": size, "type": mime_excel}
            }

            try:
                if doc_id:
                    registrar_evento(f"   -> ¡Makankosappo! Intentando REEMPLAZO (PUT) al ID: {doc_id}...")
                    r_put = requests.put(f"{base_rag_url}/{doc_id}", headers=self.headers_api, json=payload)
                    if r_put.status_code == 200:
                        registrar_evento("   [ÉXITO] ¡Documento actualizado limpiamente! Un ataque perfecto.")
                    else:
                        registrar_evento(f"   [FALLO PUT] Status {r_put.status_code}. ¡El enemigo lo esquivó! Aplicando técnica combinada (DELETE + POST)...")
                        requests.delete(f"{base_rag_url}/{doc_id}", headers=self.headers_api)
                        time.sleep(0.5)
                        r_post = requests.post(f"{base_rag_url}/add", headers=self.headers_api, json=payload)
                        r_post.raise_for_status()
                        registrar_evento("   [ÉXITO] ¡Documento recreado por contingencia! ¡Las esferas del dragón funcionan!")
                else:
                    registrar_evento("   -> ¡Es un clon fantasma! Intentando CREACIÓN (POST)...")
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