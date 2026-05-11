import os
import requests
import pandas as pd
from dotenv import load_dotenv
from logger_escala import registrar_evento

load_dotenv()

class SAPServiceLayerV2:
    def __init__(self):
        self.base_url = "https://sap-packvision-sl.skyinone.net:50000/b1s/v2"
        self.config = {
            "CompanyDB": os.getenv('CompanyDB'), 
            "UserName": os.getenv('UserName'),
            "Password": os.getenv('Password')
        }
        self.session = requests.Session()
        self.session.verify = False 
        requests.packages.urllib3.disable_warnings()
        self.sql_code = "ConsultaStockBodegasPT"
        
        self.session.headers.update({
            "Prefer": "odata.maxpagesize=500",
            "Content-Type": "application/json"
        })

    def conectar(self):
        try:
            url = f"{self.base_url}/Login"
            response = self.session.post(url, json=self.config, timeout=15)
            response.raise_for_status()
            registrar_evento("[OK] ¡Poder al máximo! Sesión iniciada como un Super Saiyajin.")
            return True
        except Exception as e:
            registrar_evento(f"[CRITICAL] ¡Gokuuuuu! ¡Krilin ha explotado! Error de autenticación: {e}")
            return False

    def registrar_o_actualizar_sql(self):
        sql_text = (
            "SELECT T0.\"ItemCode\", T0.\"ItemName\", T1.\"OnHand\" AS \"StockEnBodega\", "
            "T1.\"WhsCode\" AS \"Bodega\", T0.\"SLength1\", T0.\"SWidth1\", T0.\"SHeight1\", T0.\"SVolume\" "
            "FROM \"OITM\" T0 INNER JOIN \"OITW\" T1 ON T0.\"ItemCode\" = T1.\"ItemCode\" "
            "WHERE T0.\"validFor\" = 'Y' AND T0.\"frozenFor\" = 'N' AND T0.\"ItemCode\" LIKE 'PT%' "
            "AND T1.\"WhsCode\" IN ("
            "'B001', 'B002', 'B003', 'B010', 'B050', 'B053', 'B056', 'B059', 'B062', 'B065', 'B068', 'B069', 'B071', 'B171', 'B174', "
            "'B011', 'B051', 'B054', 'B057', 'B060', 'B063', 'B066', 'B072', 'B172', 'B176', "
            "'B012', 'B052', 'B055', 'B058', 'B061', 'B064', 'B067', 'B070', 'B073', 'B173', 'B175'"
            ") "
            "AND T1.\"OnHand\" > 0 ORDER BY T1.\"WhsCode\" ASC, T0.\"ItemCode\" ASC"
        )
        
        payload = {
            "SqlCode": self.sql_code,
            "SqlName": "Stock de Bodegas para items PT",
            "SqlText": sql_text
        }

        url = f"{self.base_url}/SQLQueries"
        response = self.session.post(url, json=payload)

        if response.status_code in (201, 204):
            registrar_evento(f"[OK] ¡Las esferas del dragón han hablado! Consulta '{self.sql_code}' creada.")
            
        elif response.status_code == 400 and "already exists" in response.text:
            registrar_evento(f"[INFO] La consulta '{self.sql_code}' ya existe. ¡Fuuuuusión... HA! Actualizando versión...")
            
            url_update = f"{self.base_url}/SQLQueries('{self.sql_code}')"
            
            patch_res = self.session.patch(url_update, json={"SqlText": sql_text})
            if patch_res.status_code == 204:
                registrar_evento("[OK] ¡Eres un guerrero orgulloso! Consulta actualizada correctamente.")
            else:
                registrar_evento(f"[ERROR] ¡Maldición, Freezer! No se pudo actualizar: {patch_res.text}")
        else:
            registrar_evento(f"[ERROR] ¡Insecto! Error inesperado: {response.text}")

    def extraer_datos_stock(self):
        self.registrar_o_actualizar_sql()
        
        url_execute = f"{self.base_url}/SQLQueries('{self.sql_code}')/List"
        todos_los_datos = []
        
        while url_execute:
            response = self.session.get(url_execute, timeout=30)
            
            if response.status_code == 401:
                self.conectar()
                continue
                
            response.raise_for_status()
            json_data = response.json()
            
            datos_pagina = json_data.get('value', [])
            todos_los_datos.extend(datos_pagina)
            
            next_link = json_data.get('@odata.nextLink')
            if next_link:
                if next_link.startswith('http'):
                    url_execute = next_link
                else:
                    ruta_limpia = next_link.replace('/b1s/v2/', '')
                    url_execute = f"{self.base_url}/{ruta_limpia}"
            else:
                url_execute = None
        
        registrar_evento(f"[INFO] ¡KAME HAME HAAAA! La Genkidama está lista. Total de filas recuperadas: {len(todos_los_datos)}... ¡Siempre te recordaré Majin Buu!")
        return pd.DataFrame(todos_los_datos)