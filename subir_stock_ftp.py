import ftplib
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / '.env')

CSV_LOCAL  = Path(__file__).parent / 'Listado_generico_SAP_.csv'
RUTA_REMOTA = '/public_html/api/data/stock_generico.csv'

def subir_csv():
    if not CSV_LOCAL.exists():
        print(f"❌ No existe el CSV: {CSV_LOCAL}")
        return False

    try:
        ftp = ftplib.FTP()
        ftp.connect(
            host=os.getenv('FTP_HOST'),
            port=int(os.getenv('FTP_PORT', 21)),
            timeout=30
        )
        ftp.login(
            user=os.getenv('FTP_USER'),
            passwd=os.getenv('FTP_PASS')
        )

        # Crear carpeta si no existe
        try:
            ftp.mkd('/public_html/api/data')
        except ftplib.error_perm:
            pass  # ya existe

        # Subir el archivo
        with open(CSV_LOCAL, 'rb') as f:
            ftp.storbinary(f'STOR {RUTA_REMOTA}', f)

        ftp.quit()
        print(f"✅ CSV subido exitosamente → {RUTA_REMOTA}")
        return True

    except Exception as e:
        print(f"❌ Error FTP: {e}")
        return False

if __name__ == '__main__':
    subir_csv()