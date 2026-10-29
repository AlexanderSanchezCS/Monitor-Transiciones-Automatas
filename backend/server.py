"""Servidor HTTP y API de la aplicación web del monitor."""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from monitor.automata import ACCEPTING_STATES, ALPHABET, AUTOMATON_STATES, TRANSITIONS
from monitor.monitor import EVENTS, PATTERNS, analyze_sequence, generated_summary, load_dataset_sessions


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _serve_frontend(self) -> None:
        requested = urlparse(self.path).path
        relative = "index.html" if requested == "/" else requested.removeprefix("/")
        target = (FRONTEND / relative).resolve()
        if FRONTEND not in target.parents or not target.is_file():
            self.send_error(404)
            return
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
        }.get(target.suffix, "application/octet-stream")
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/summary":
            self._send(generated_summary(ROOT))
        elif parsed.path == "/api/patterns":
            self._send(PATTERNS)
        elif parsed.path == "/api/events":
            self._send([{"symbol": key, "name": value} for key, value in EVENTS.items()])
        elif parsed.path == "/api/sessions":
            dataset = parse_qs(parsed.query).get("dataset", ["validation"])[0]
            if dataset not in {"validation", "test"}:
                self._send({"error": "Conjunto inválido. Usa validation o test."}, 400)
                return
            self._send(load_dataset_sessions(ROOT, dataset))
        elif parsed.path == "/api/automaton":
            self._send({
                "states": AUTOMATON_STATES,
                "transitions": TRANSITIONS,
                "alphabet": list(ALPHABET),
                "initial": "M0",
                "accepting": sorted(ACCEPTING_STATES),
                "models": {"afnd": 11, "afd": 37, "minimal": 4},
            })
        elif parsed.path.startswith("/api/analyze/"):
            sequence = parsed.path.removeprefix("/api/analyze/").upper()
            if not sequence or not re.fullmatch(f"[{''.join(ALPHABET)}]+", sequence):
                self._send({"error": "La secuencia contiene símbolos fuera del alfabeto."}, 400)
            else:
                self._send(analyze_sequence(sequence))
        else:
            self._serve_frontend()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/analyze":
            self._send({"error": "Ruta no encontrada."}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
            sequence = str(data.get("sequence", "")).strip().upper()
        except (ValueError, json.JSONDecodeError):
            self._send({"error": "Solicitud JSON inválida."}, 400)
            return
        if not sequence or not re.fullmatch(f"[{''.join(ALPHABET)}]+", sequence):
            self._send({"error": "Ingresa una cadena usando únicamente B, P, F, C, X, D, R o V."}, 400)
            return
        self._send(analyze_sequence(sequence))

    def log_message(self, format: str, *args: Any) -> None:
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Monitor disponible en http://localhost:{port}")
    ThreadingHTTPServer(("localhost", port), Handler).serve_forever()
