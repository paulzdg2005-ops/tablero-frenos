"""Abre el tablero como programa de escritorio (ventana propia). Si pywebview no está instalado, usa el navegador."""
import os, socket, subprocess, sys, time, webbrowser

CARPETA = os.path.dirname(os.path.abspath(__file__))
PUERTO = 8517
URL = f"http://localhost:{PUERTO}"


def listo(espera=40):
    t = time.time()
    while time.time() - t < espera:
        try:
            with socket.create_connection(("localhost", PUERTO), timeout=1):
                return True
        except OSError:
            time.sleep(0.4)
    return False


flags = 0x08000000 if os.name == "nt" else 0
python = sys.executable.replace("pythonw.exe", "python.exe")
log = open(os.path.join(CARPETA, "registro.txt"), "w", encoding="utf-8")
srv = subprocess.Popen([python, "-m", "streamlit", "run", os.path.join(CARPETA, "app.py"), "--server.port", str(PUERTO),
                        "--server.headless", "true"], cwd=CARPETA, stdout=log, stderr=log, creationflags=flags)
try:
    if not listo():
        raise RuntimeError("Streamlit no arrancó. Revise registro.txt")
    try:
        import webview
        webview.create_window("Tablero de condición · Frenos de aire", URL, width=1450, height=920, min_size=(1100, 700))
        webview.start()
    except ImportError:
        webbrowser.open(URL)
        srv.wait()
finally:
    srv.terminate()
    log.close()
