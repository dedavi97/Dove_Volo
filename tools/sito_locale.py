"""Apre il sito sul PC: i browser non leggono i dati se la pagina si apre col doppio clic."""
import functools
import http.server
import webbrowser
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PORTE = (8765, 8766, 8767, 0)  # 0 = una porta libera qualsiasi


class Pagine(http.server.SimpleHTTPRequestHandler):
    # Scritti qui: i tipi letti da Windows a volte sono sbagliati e bloccano i moduli JavaScript.
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".js": "text/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".json": "application/json",
        ".png": "image/png",
    }

    def log_message(self, *argomenti):
        pass


def crea_server():
    gestore = functools.partial(Pagine, directory=str(RADICE))
    for porta in PORTE:
        try:
            # Solo 127.0.0.1: il sito si vede da questo PC, non dagli altri in rete.
            return http.server.ThreadingHTTPServer(("127.0.0.1", porta), gestore)
        except OSError:
            continue
    raise OSError("Nessuna porta disponibile")


def main():
    server = crea_server()
    indirizzo = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Dove_Volo e' aperto su {indirizzo}")
    print("Per chiudere premi Ctrl+C o chiudi questa finestra.")
    webbrowser.open(indirizzo)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
