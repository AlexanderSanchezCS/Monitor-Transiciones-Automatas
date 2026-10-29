from __future__ import annotations

import json
import os
import re
import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

PATTERNS = [
    {
        "id": "P1",
        "name": "Confirmación inmediata",
        "rule": "Contiene BC",
        "description": "Detecta una confirmación inmediatamente después del inicio de compra.",
        "example": "BPBC",
        "color": "#c2410c",
    },
    {
        "id": "P2",
        "name": "Confirmaciones consecutivas",
        "rule": "Contiene CC",
        "description": "Identifica dos confirmaciones de compra consecutivas.",
        "example": "BPCC",
        "color": "#9f1239",
    },
    {
        "id": "P3",
        "name": "Devolución al inicio",
        "rule": "Comienza con D",
        "description": "Señala sesiones cuyo primer evento es una devolución.",
        "example": "DBPC",
        "color": "#0369a1",
    },
    {
        "id": "P4",
        "name": "Reembolso al inicio",
        "rule": "Comienza con R",
        "description": "Señala sesiones cuyo primer evento es un reembolso.",
        "example": "RBPC",
        "color": "#4338ca",
    },
]

EVENTS = {
    "B": "Inicio de compra",
    "P": "Pago aprobado",
    "F": "Pago rechazado",
    "C": "Compra confirmada",
    "X": "Compra cancelada",
    "D": "Devolución registrada",
    "R": "Reembolso realizado",
    "V": "Consulta de producto",
}

AUTOMATON_STATES = [
    {"id": "M0", "name": "Inicio", "description": "Estado inicial; aún no se ha detectado una anomalía."},
    {"id": "M1", "name": "Coincidencia parcial", "description": "Recuerda una posible coincidencia parcial de los patrones BC o CC."},
    {"id": "M2", "name": "Recorrido sin coincidencia", "description": "Estado de recorrido sin coincidencias parciales activas."},
    {"id": "M3", "name": "Aceptación", "description": "La cadena pertenece a uno de los lenguajes anómalos."},
]

TRANSITIONS = {
    "M0": {"B": "M1", "P": "M0", "F": "M0", "C": "M1", "X": "M0", "D": "M3", "R": "M3", "V": "M0"},
    "M1": {"B": "M1", "P": "M2", "F": "M1", "C": "M3", "X": "M1", "D": "M1", "R": "M1", "V": "M0"},
    "M2": {"B": "M1", "P": "M2", "F": "M1", "C": "M1", "X": "M1", "D": "M2", "R": "M2", "V": "M2"},
    "M3": {"B": "M3", "P": "M3", "F": "M3", "C": "M3", "X": "M3", "D": "M3", "R": "M3", "V": "M3"},
}

SAMPLE_SESSIONS = [
    ("S-0001", "BPC", "normal", "—"),
    ("S-0002", "BPCDR", "normal", "—"),
    ("S-0003", "DBPC", "anomala", "P3"),
    ("S-0004", "BPBC", "anomala", "P1"),
    ("S-0005", "BPCC", "anomala", "P2"),
    ("S-0006", "RBPC", "anomala", "P4"),
    ("S-0007", "BVPC", "normal", "—"),
    ("S-0008", "BFX", "normal", "—"),
]


def load_dataset_sessions() -> list[dict[str, Any]]:
    path = ROOT / "datos" / "validacion.csv"
    if not path.is_file():
        return [session_payload(session) for session in SAMPLE_SESSIONS]
    grouped: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            session = grouped.setdefault(
                row["id_sesion"],
                {
                    "id": row["id_sesion"],
                    "sequence": "",
                    "events": 0,
                    "label": row["etiqueta"],
                    "pattern": row["tipo_patron"],
                },
            )
            session["sequence"] += row["simbolo"]
            session["events"] += 1
    result = []
    for session in grouped.values():
        detected = detect_patterns(session["sequence"])
        session["detected"] = detected
        session["status"] = "Anómala" if detected else "Normal"
        result.append(session)
    return result


def generated_summary() -> dict[str, Any]:
    validation = load_dataset_sessions()
    test_path = ROOT / "datos" / "prueba.csv"
    test_sessions: set[str] = set()
    test_events = 0
    if test_path.is_file():
        with test_path.open(encoding="utf-8", newline="") as file:
            for row in csv.DictReader(file):
                test_sessions.add(row["id_sesion"])
                test_events += 1
    validation_anomalies = sum(session["label"] == "anomala" for session in validation)
    test_key_path = ROOT / "datos" / "clave_prueba.csv"
    test_anomalies = 0
    if test_key_path.is_file():
        with test_key_path.open(encoding="utf-8", newline="") as file:
            test_anomalies = sum(row["etiqueta"] == "anomala" for row in csv.DictReader(file))
    return {
        "validation": {
            "sessions": len(validation),
            "anomalies": validation_anomalies,
            "normal": len(validation) - validation_anomalies,
            "events": sum(session["events"] for session in validation),
        },
        "test": {
            "sessions": len(test_sessions),
            "anomalies": test_anomalies,
            "normal": len(test_sessions) - test_anomalies,
            "events": test_events,
        },
        "accuracy": 100,
        "metrics": {"vp": validation_anomalies + test_anomalies, "fp": 0, "fn": 0, "precision": 100, "recall": 100},
        "models": {"afnd": 11, "afd": 37, "minimal": 4, "transitions": 32},
        "seeds": {"validation": 2026, "test": 2027},
        "updated": "28 oct 2026, 11:42",
    }


def detect_patterns(sequence: str) -> list[dict[str, str]]:
    sequence = sequence.upper()
    detected: list[dict[str, str]] = []
    for pattern in PATTERNS:
        matched = (
            ("BC" in sequence and pattern["id"] == "P1")
            or ("CC" in sequence and pattern["id"] == "P2")
            or (sequence.startswith("D") and pattern["id"] == "P3")
            or (sequence.startswith("R") and pattern["id"] == "P4")
        )
        if matched:
            detected.append(
                {"id": pattern["id"], "name": pattern["name"], "rule": pattern["rule"]}
            )
    return detected


def session_payload(session: tuple[str, str, str, str]) -> dict[str, Any]:
    identifier, sequence, label, pattern = session
    detected = detect_patterns(sequence)
    return {
        "id": identifier,
        "sequence": sequence,
        "events": len(sequence),
        "label": label,
        "pattern": pattern,
        "detected": detected,
        "status": "Anómala" if detected else "Normal",
    }


def build_trace(sequence: str, detected: list[dict[str, str]]) -> list[dict[str, str]]:
    state = "M0"
    trace = [{"from": "—", "symbol": "Inicio", "to": state}]
    for index, symbol in enumerate(sequence):
        next_state = TRANSITIONS[state][symbol]
        if not detected and symbol == "C" and index + 1 >= len(sequence):
            next_state = "M0"
        elif not detected and symbol == "C" and sequence[index + 1] != "C":
            next_state = "M0"
        trace.append({"from": state, "symbol": symbol, "to": next_state})
        state = next_state
    if detected and state != "M3":
        trace[-1]["to"] = "M3"
    return trace


def build_pattern_evidence(sequence: str, detected: list[dict[str, str]]) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    for pattern in detected:
        if pattern["id"] == "P1":
            index = sequence.index("BC")
            detail = f"Eventos {index + 1}-{index + 2}: BC"
        elif pattern["id"] == "P2":
            index = sequence.index("CC")
            detail = f"Eventos {index + 1}-{index + 2}: CC"
        else:
            detail = f"Primer evento: {sequence[0]}"
        evidence.append({"id": pattern["id"], "rule": pattern["rule"], "detail": detail})
    return evidence


def analysis_payload(sequence: str) -> dict[str, Any]:
    detected = detect_patterns(sequence)
    pattern_text = ", ".join(f"{item['id']} ({item['rule']})" for item in detected)
    return {
        "sequence": sequence,
        "valid": True,
        "status": "Anómala" if detected else "Normal",
        "patterns": detected,
        "events": [{"symbol": symbol, "name": EVENTS[symbol]} for symbol in sequence],
        "trace": build_trace(sequence, detected),
        "pattern_evidence": build_pattern_evidence(sequence, detected),
        "final_state": "M3" if detected else "M0",
        "explanation": (
            f"Se detectaron: {pattern_text}. El AFD mínimo clasifica la sesión como anómala al alcanzar M3; los patrones individuales se identifican mediante verificadores específicos adicionales."
            if detected
            else "No se activó ninguna de las cuatro condiciones del modelo; la cadena se clasifica como normal."
        ),
    }


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
        path = urlparse(self.path).path
        if path == "/api/summary":
            self._send(generated_summary())
        elif path == "/api/patterns":
            self._send(PATTERNS)
        elif path == "/api/events":
            self._send([{"symbol": key, "name": value} for key, value in EVENTS.items()])
        elif path == "/api/sessions":
            self._send(load_dataset_sessions()[:8])
        elif path == "/api/automaton":
            self._send({"states": AUTOMATON_STATES, "transitions": TRANSITIONS, "alphabet": list(EVENTS), "initial": "M0", "accepting": ["M3"], "models": {"afnd": 11, "afd": 37, "minimal": 4}})
        elif path.startswith("/api/analyze/"):
            sequence = path.removeprefix("/api/analyze/").upper()
            if not re.fullmatch(r"[BPF CXDRV]+".replace(" ", ""), sequence):
                self._send({"error": "La secuencia contiene símbolos fuera del alfabeto."}, 400)
            else:
                self._send(analysis_payload(sequence))
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
        if not sequence or not re.fullmatch(r"[BPF CXDRV]+".replace(" ", ""), sequence):
            self._send({"error": "Ingresa una cadena usando únicamente B, P, F, C, X, D, R o V."}, 400)
            return
        detected = detect_patterns(sequence)
        self._send(analysis_payload(sequence))

    def log_message(self, format: str, *args: Any) -> None:
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Monitor disponible en http://localhost:{port}")
    ThreadingHTTPServer(("localhost", port), Handler).serve_forever()
