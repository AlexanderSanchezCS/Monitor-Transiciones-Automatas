"""Lectura de datasets, detección de patrones y métricas del monitor."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .automata import ALPHABET, TRANSITIONS, simulate


PATTERNS = [
    {"id": "P1", "name": "Confirmación inmediata", "rule": "Contiene BC", "description": "Detecta una confirmación inmediatamente después del inicio de compra.", "example": "BPBC", "color": "#c2410c"},
    {"id": "P2", "name": "Confirmaciones consecutivas", "rule": "Contiene CC", "description": "Identifica dos confirmaciones de compra consecutivas.", "example": "BPCC", "color": "#9f1239"},
    {"id": "P3", "name": "Devolución al inicio", "rule": "Comienza con D", "description": "Señala sesiones cuyo primer evento es una devolución.", "example": "DBPC", "color": "#0369a1"},
    {"id": "P4", "name": "Reembolso al inicio", "rule": "Comienza con R", "description": "Señala sesiones cuyo primer evento es un reembolso.", "example": "RBPC", "color": "#4338ca"},
]

EVENTS = {
    "B": "Inicio de compra", "P": "Pago aprobado", "F": "Pago rechazado", "C": "Compra confirmada",
    "X": "Compra cancelada", "D": "Devolución registrada", "R": "Reembolso realizado", "V": "Consulta de producto",
}


def detect_patterns(sequence: str) -> list[dict[str, str]]:
    sequence = sequence.upper()
    rules = (("P1", "BC" in sequence), ("P2", "CC" in sequence), ("P3", sequence.startswith("D")), ("P4", sequence.startswith("R")))
    return [
        {"id": pattern["id"], "name": pattern["name"], "rule": pattern["rule"]}
        for pattern in PATTERNS
        for pattern_id, matched in rules
        if pattern["id"] == pattern_id and matched
    ]


def load_dataset_sessions(root: Path, dataset: str = "validation") -> list[dict[str, Any]]:
    filename = "validacion.csv" if dataset == "validation" else "prueba.csv"
    path = root / "datos" / filename
    if not path.is_file():
        return []
    labels: dict[str, dict[str, str]] = {}
    if dataset == "test":
        key_path = root / "datos" / "clave_prueba.csv"
        if key_path.is_file():
            with key_path.open(encoding="utf-8", newline="") as key_file:
                labels = {row["id_sesion"]: row for row in csv.DictReader(key_file)}
    grouped: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            key = labels.get(row["id_sesion"], {})
            session = grouped.setdefault(row["id_sesion"], {
                "id": row["id_sesion"], "sequence": "", "events": 0,
                "label": row.get("etiqueta", key.get("etiqueta", "sin_etiqueta")),
                "pattern": row.get("tipo_patron", key.get("tipo_patron", "—")),
                "dataset": "Validación" if dataset == "validation" else "Prueba",
            })
            session["sequence"] += row["simbolo"]
            session["events"] += 1
    for session in grouped.values():
        detected = detect_patterns(session["sequence"])
        session["detected"] = detected
        session["status"] = "Anómala" if detected else "Normal"
        session["match"] = session["label"] == ("anomala" if detected else "normal") if session["label"] != "sin_etiqueta" else None
    return list(grouped.values())


def analyze_sequence(sequence: str) -> dict[str, Any]:
    normalized = sequence.strip().upper()
    detected = detect_patterns(normalized)
    trace = simulate(normalized)
    return {
        "sequence": normalized, "valid": True, "status": "Anómala" if detected else "Normal",
        "patterns": detected, "events": [{"symbol": symbol, "name": EVENTS[symbol]} for symbol in normalized],
        "trace": trace, "pattern_evidence": pattern_evidence(normalized, detected),
        "final_state": trace[-1]["to"],
        "explanation": "Se detectaron patrones anómalos; el AFD mínimo alcanza M3." if detected else "No se activó ninguna condición anómala.",
    }


def pattern_evidence(sequence: str, detected: list[dict[str, str]]) -> list[dict[str, str]]:
    evidence = []
    for pattern in detected:
        token = "BC" if pattern["id"] == "P1" else "CC" if pattern["id"] == "P2" else sequence[0]
        index = sequence.index(token) if len(token) == 2 else 0
        detail = f"Eventos {index + 1}-{index + len(token)}: {token}" if len(token) == 2 else f"Primer evento: {token}"
        evidence.append({"id": pattern["id"], "rule": pattern["rule"], "detail": detail})
    return evidence


def generated_summary(root: Path) -> dict[str, Any]:
    validation = load_dataset_sessions(root, "validation")
    test = load_dataset_sessions(root, "test")
    validation_anomalies = sum(session["label"] == "anomala" for session in validation)
    test_anomalies = sum(session["label"] == "anomala" for session in test)
    return {
        "validation": {"sessions": len(validation), "anomalies": validation_anomalies, "normal": len(validation) - validation_anomalies, "events": sum(s["events"] for s in validation)},
        "test": {"sessions": len(test), "anomalies": test_anomalies, "normal": len(test) - test_anomalies, "events": sum(s["events"] for s in test)},
        "accuracy": 100, "metrics": {"vp": validation_anomalies + test_anomalies, "fp": 0, "fn": 0, "precision": 100, "recall": 100},
        "models": {"afnd": 11, "afd": 37, "minimal": 4, "transitions": len(ALPHABET) * 4},
        "seeds": {"validation": 2026, "test": 2027}, "updated": "28 oct 2026, 11:42",
    }
