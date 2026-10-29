"""Lectura de datasets, detección de patrones y métricas del monitor."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from .automata import ALPHABET, accepts, simulate


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
        is_anomalous = accepts(session["sequence"])
        session["status"] = "Anómala" if is_anomalous else "Normal"
        session["match"] = session["label"] == ("anomala" if is_anomalous else "normal") if session["label"] != "sin_etiqueta" else None
    return list(grouped.values())


def analyze_sequence(sequence: str) -> dict[str, Any]:
    normalized = sequence.strip().upper()
    detected = detect_patterns(normalized)
    trace = simulate(normalized)
    is_anomalous = accepts(normalized)
    return {
        "sequence": normalized, "valid": True, "status": "Anómala" if is_anomalous else "Normal",
        "patterns": detected, "events": [{"symbol": symbol, "name": EVENTS[symbol]} for symbol in normalized],
        "trace": trace, "pattern_evidence": pattern_evidence(normalized, detected),
        "final_state": trace[-1]["to"],
        "explanation": "El AFD mínimo alcanza M3; los verificadores identifican los patrones." if is_anomalous else "El AFD termina fuera de M3; la cadena se clasifica como normal.",
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
    validation_metrics = calculate_metrics(validation)
    test_metrics = calculate_metrics(test)
    combined = calculate_metrics(validation + test)
    return {
        "validation": {"sessions": len(validation), "anomalies": validation_metrics["expected_anomalies"], "normal": validation_metrics["tn"] + validation_metrics["fp"], "events": sum(s["events"] for s in validation), "metrics": validation_metrics},
        "test": {"sessions": len(test), "anomalies": test_metrics["expected_anomalies"], "normal": test_metrics["tn"] + test_metrics["fp"], "events": sum(s["events"] for s in test), "metrics": test_metrics},
        "accuracy": combined["accuracy"], "metrics": combined,
        "models": {"afnd": None, "afd": None, "minimal": 4, "transitions": len(ALPHABET) * 4},
        "seeds": {"validation": 2026, "test": 2027},
        "updated": datetime.now().astimezone().strftime("%d %b %Y, %H:%M"),
    }


def calculate_metrics(sessions: list[dict[str, Any]]) -> dict[str, float | int]:
    """Calcula métricas comparando la etiqueta esperada con la decisión del AFD."""
    labeled = [session for session in sessions if session["label"] != "sin_etiqueta"]
    true_positive = sum(session["label"] == "anomala" and session["match"] for session in labeled)
    false_positive = sum(session["label"] == "normal" and session["status"] == "Anómala" for session in labeled)
    false_negative = sum(session["label"] == "anomala" and session["status"] == "Normal" for session in labeled)
    true_negative = sum(session["label"] == "normal" and session["status"] == "Normal" for session in labeled)
    total = len(labeled)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
    return {
        "vp": true_positive, "fp": false_positive, "fn": false_negative,
        "tn": true_negative, "expected_anomalies": true_positive + false_negative,
        "accuracy": round((true_positive + true_negative) / total * 100, 2) if total else 0,
        "precision": round(precision * 100, 2), "recall": round(recall * 100, 2),
    }


def console_report(root: Path, dataset: str = "test") -> str:
    sessions = load_dataset_sessions(root, dataset)
    metrics = calculate_metrics(sessions)
    return (
        f"Conjunto: {dataset}\n"
        f"Sesiones: {len(sessions)}\n"
        f"VP={metrics['vp']} FP={metrics['fp']} FN={metrics['fn']} TN={metrics['tn']}\n"
        f"Precisión={metrics['precision']}% Recall={metrics['recall']}% Exactitud={metrics['accuracy']}%\n"
        f"Estados mínimos={4} Transiciones={len(ALPHABET) * 4}\n"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ejecuta el informe de métricas del monitor.")
    parser.add_argument("dataset", choices=("validation", "test"), nargs="?", default="test")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(console_report(args.root, args.dataset), end="")
