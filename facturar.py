import os
import sys
import time
import pathlib
import argparse
from datetime import datetime
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

if not os.getenv("CI"):
    load_dotenv()

credentials = {
    "CUIT": os.getenv("CUIT"),
    "PASSWORD": os.getenv("PASSWORD"),
    "COMPANY": os.getenv("COMPANY"),
}

def format_day():
    return datetime.now().strftime("%Y%m%d")

def format_time():
    return datetime.now().strftime("%H%M%S")

def ensure_dir(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

def verify():
    parser = argparse.ArgumentParser(description="Generador automático de facturas AFIP")
    parser.add_argument("--amount", type=str, default="200000", help="Monto de la factura (default: 200000)")
    parser.add_argument("--iva", type=int, choices=[1, 3], default=3, help="Tipo de receptor: 1 = IVA RI, 3 = Consumidor Final (default: 3)")
    parser.add_argument("--cuit", type=str, help="CUIT del receptor (requerido si --iva 1)")

    args = parser.parse_args()

    amount = args.amount
    iva_option = str(args.iva)
    receptor_cuit = args.cuit

    if iva_option == "1" and not receptor_cuit:
        print("❌ Debe ingresar el CUIT del receptor con --cuit si selecciona --iva 1 (IVA Responsable Inscripto).")
        return

    print(f"✅ Argumentos: amount={amount}, iva={iva_option}, receptor_cuit={receptor_cuit or 'N/A'}")

    output_path = f"output/{format_day()}"
    ensure_dir(output_path)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50, args=["--start-maximized"])
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto("https://auth.afip.gob.ar/contribuyente_/login.xhtml?action=SYSTEM&system=rcel")
            page.fill('input[name="F1:username"]', credentials["CUIT"])
            time.sleep(1)
            page.click('input[name="F1:btnSiguiente"]')
            time.sleep(1)
            page.fill('input[name="F1:password"]', credentials["PASSWORD"])
            time.sleep(1)
            page.click('input[name="F1:btnIngresar"]')
            time.sleep(2)
            page.click(f'input[value="{credentials["COMPANY"]}"]')
            time.sleep(1)
            page.click("#btn_gen_cmp")
            time.sleep(1)
            page.select_option('select[name="puntoDeVenta"]', "1")
            time.sleep(1)
            page.click("#contenido > form > input[type=button]:nth-child(4)")
            time.sleep(1)
            page.select_option("#idconcepto", index=2)
            page.click("#contenido > form > input[type=button]:nth-child(4)")
            time.sleep(1)
            page.select_option("#idivareceptor", index=int(iva_option))
            time.sleep(1)

            if iva_option == "1":
                print(f"✍️ Completando CUIT del receptor: {receptor_cuit}")
                page.fill("#nrodocreceptor", receptor_cuit)
                time.sleep(1)

            page.check("input#formadepago7")
            page.click("#formulario > input[type=button]:nth-child(4)")
            time.sleep(1)
            page.fill("#detalle_descripcion1", "Servicios Informáticos")
            page.fill("#detalle_precio1", amount)
            time.sleep(1)
            page.click("#contenido > form > input[type=button]:nth-child(15)")
            time.sleep(1)
            page.once("dialog", lambda dialog: dialog.accept())
            time.sleep(2)

            screenshot_path = f"{output_path}/success_{format_day()}_{format_time()}.png"
            page.screenshot(path=screenshot_path)
            print(f"✅ Factura generada. Screenshot guardado en: {screenshot_path}")
        except Exception as e:
            print(f"❌ Error: {e}")
            error_path = f"{output_path}/error_{format_day()}_{format_time()}.png"
            try:
                page.screenshot(path=error_path)
                print(f"📸 Error capturado en: {error_path}")
            except Exception as screenshot_error:
                print(f"⚠️ No se pudo capturar screenshot de error: {screenshot_error}")
        finally:
            browser.close()

if __name__ == "__main__":
    verify()
