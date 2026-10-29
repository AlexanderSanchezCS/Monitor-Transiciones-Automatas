"""Genera los conjuntos sintéticos reproducibles del monitor.

Uso:
    python datos/generador.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ALPHABET = frozenset("BPF CXDRV".replace(" ", ""))
TEMPLATES = ("BPC", "BPCDR", "BFBPC", "BX", "BFX")
NEAR_ANOMALOUS = {
    "P1": ("BVC", "BPXC"),
    "P2": ("CVC", "CPC"),
    "P3": ("VD", "BD"),
    "P4": ("VR", "BPR"),
}
ANOMALY_COUNTS = {
    "validation": {"P1": 14, "P2": 14, "P3": 13, "P4": 13},
    "test": {"P1": 3, "P2": 3, "P3": 3, "P4": 2},
}
TOTALS = {"validation": 300, "test": 60}
EVENT_TOTALS = {"validation": 1557, "test": 309}
MAX_LENGTHS = {"validation": 10, "test": 9}
SEEDS = {"validation": 2026, "test": 2027}

EVENT_NAMES = {
    "B": "INICIO_COMPRA",
    "P": "PAGO_APROBADO",
    "F": "PAGO_RECHAZADO",
    "C": "COMPRA_CONFIRMADA",
    "X": "COMPRA_CANCELADA",
    "D": "DEVOLUCION_REGISTRADA",
    "R": "REEMBOLSO_REALIZADO",
    "V": "CONSULTA_PRODUCTO",
}
ACTORS = {
    "B": "cliente",
    "P": "pasarela_pago",
    "F": "pasarela_pago",
    "C": "sistema_tienda",
    "X": "cliente",
    "D": "servicio_devoluciones",
    "R": "servicio_reembolsos",
    "V": "cliente",
}


@dataclass(frozen=True)
class Session:
    session_id: str
    sequence: str
    label: str
    pattern: str
    source: str


def detected_patterns(sequence: str) -> tuple[str, ...]:
    patterns = []
    if "BC" in sequence:
        patterns.append("P1")
    if "CC" in sequence:
        patterns.append("P2")
    if sequence.startswith("D"):
        patterns.append("P3")
    if sequence.startswith("R"):
        patterns.append("P4")
    return tuple(patterns)


def insert_queries(template: str, rng: random.Random) -> str:
    result = list(template)
    for _ in range(rng.randint(0, 3)):
        result.insert(rng.randint(0, len(result)), "V")
    return "".join(result)


def inject_anomaly(template: str, pattern: str, rng: random.Random) -> str:
    if pattern == "P1":
        position = rng.randint(0, len(template))
        return template[:position] + "BC" + template[position:]
    if pattern == "P2":
        position = template.index("C") + 1
        return template[:position] + "C" + template[position:]
    if pattern == "P3":
        return "D" + template
    if pattern == "P4":
        return "R" + template
    raise ValueError(f"Patrón no soportado: {pattern}")


def complete_sequence(sequence: str) -> str:
    return sequence + "V" * max(0, 3 - len(sequence))


def build_anomaly(pattern: str, rng: random.Random) -> str:
    for _ in range(100):
        templates = tuple(template for template in TEMPLATES if pattern != "P2" or "C" in template)
        sequence = complete_sequence(
            inject_anomaly(insert_queries(rng.choice(templates), rng), pattern, rng)
        )
        if detected_patterns(sequence) == (pattern,) and 3 <= len(sequence) <= 20:
            return sequence
    raise RuntimeError(f"No se pudo construir una sesión exclusiva para {pattern}")


def build_normal(rng: random.Random) -> str:
    sequence = complete_sequence(insert_queries(rng.choice(TEMPLATES), rng))
    if detected_patterns(sequence):
        raise RuntimeError(f"Plantilla normal inválida: {sequence}")
    return sequence


def build_sessions(dataset: str) -> list[Session]:
    rng = random.Random(SEEDS[dataset])
    total = TOTALS[dataset]
    anomaly_counts = ANOMALY_COUNTS[dataset]
    near_count = 40 if dataset == "validation" else 8
    sessions: list[Session] = []

    for pattern, count in anomaly_counts.items():
        for _ in range(count):
            sessions.append(Session("", build_anomaly(pattern, rng), "anomala", pattern, "inyectada"))

    near_sequences = [value for values in NEAR_ANOMALOUS.values() for value in values]
    for index in range(near_count):
        pattern = tuple(NEAR_ANOMALOUS)[index % len(NEAR_ANOMALOUS)]
        sequence = near_sequences[index % len(near_sequences)]
        sessions.append(Session("", complete_sequence(sequence), "normal", "—", f"casi_{pattern}"))

    regular_count = total - sum(anomaly_counts.values()) - near_count
    for _ in range(regular_count):
        sessions.append(Session("", build_normal(rng), "normal", "—", "plantilla_normal"))

    sessions = ensure_documented_maximum(sessions, MAX_LENGTHS[dataset])
    sessions = adjust_event_total(sessions, EVENT_TOTALS[dataset])
    rng.shuffle(sessions)
    prefix = "S" if dataset == "validation" else "T"
    return [
        Session(f"{prefix}-{index:04d}", session.sequence, session.label, session.pattern, session.source)
        for index, session in enumerate(sessions, 1)
    ]


def ensure_documented_maximum(sessions: list[Session], maximum: int) -> list[Session]:
    if max(len(session.sequence) for session in sessions) >= maximum:
        return sessions
    for index, session in enumerate(sessions):
        if session.pattern == "P1":
            sequence = "BFBPCBC" + "V" * (maximum - 7)
            sessions[index] = Session(session.session_id, sequence, session.label, session.pattern, session.source)
            return sessions
    raise AssertionError("No se encontró una sesión P1 para cubrir la longitud máxima")


def adjust_event_total(sessions: list[Session], target: int) -> list[Session]:
    current = sum(len(session.sequence) for session in sessions)
    delta = target - current
    adjusted = list(sessions)
    for index, session in enumerate(adjusted):
        if session.source != "plantilla_normal":
            continue
        sequence = session.sequence
        if delta > 0 and len(sequence) < 10 and sequence.count("V") < 3:
            sequence += "V"
            delta -= 1
        elif delta < 0 and len(sequence) > 3 and "V" in sequence:
            sequence = sequence.replace("V", "", 1)
            delta += 1
        adjusted[index] = Session(session.session_id, sequence, session.label, session.pattern, session.source)
        if delta == 0:
            break
    if delta:
        raise AssertionError(f"No se pudo alcanzar el total de eventos {target}; diferencia restante: {delta}")
    return adjusted


def rows_for_sessions(sessions: list[Session], include_labels: bool) -> list[dict[str, str]]:
    start = datetime(2026, 9, 1, 8, 0, 0)
    rows = []
    event_id = 1
    for session in sessions:
        for offset, symbol in enumerate(session.sequence):
            timestamp = start + timedelta(seconds=event_id * 37 + offset * 11)
            row = {
                "id_evento": f"E-{event_id:05d}",
                "fecha_hora": timestamp.isoformat(sep=" "),
                "id_sesion": session.session_id,
                "actor": ACTORS[symbol],
                "evento": EVENT_NAMES[symbol],
                "simbolo": symbol,
            }
            if include_labels:
                row["etiqueta"] = session.label
                row["tipo_patron"] = session.pattern
            rows.append(row)
            event_id += 1
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"No hay filas para escribir en {path}")
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_key(path: Path, sessions: list[Session]) -> None:
    rows = [
        {"id_sesion": session.session_id, "etiqueta": session.label, "tipo_patron": session.pattern}
        for session in sessions
    ]
    write_csv(path, rows)


def write_audit(path: Path, datasets: dict[str, list[Session]]) -> None:
    rows = []
    for dataset, sessions in datasets.items():
        for session in sessions:
            detected = detected_patterns(session.sequence)
            rows.append(
                {
                    "conjunto": dataset,
                    "id_sesion": session.session_id,
                    "secuencia": session.sequence,
                    "longitud": str(len(session.sequence)),
                    "origen": session.source,
                    "etiqueta_esperada": session.label,
                    "tipo_patron": session.pattern,
                    "patrones_detectados": "|".join(detected) or "—",
                    "consistente": str((session.pattern == "—" and not detected) or (detected == (session.pattern,))).lower(),
                }
            )
    write_csv(path, rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(sessions: list[Session], dataset: str) -> None:
    expected_total = TOTALS[dataset]
    if len(sessions) != expected_total:
        raise AssertionError(f"{dataset}: se esperaban {expected_total} sesiones")
    if any(not 3 <= len(session.sequence) <= 20 for session in sessions):
        raise AssertionError(f"{dataset}: hay una sesión fuera del rango 3..20")
    if sum(len(session.sequence) for session in sessions) != EVENT_TOTALS[dataset]:
        raise AssertionError(f"{dataset}: total de eventos incorrecto")
    if max(len(session.sequence) for session in sessions) != MAX_LENGTHS[dataset]:
        raise AssertionError(f"{dataset}: longitud máxima incorrecta")
    if any(set(session.sequence) - ALPHABET for session in sessions):
        raise AssertionError(f"{dataset}: hay símbolos fuera del alfabeto")
    if sum(session.label == "anomala" for session in sessions) != sum(ANOMALY_COUNTS[dataset].values()):
        raise AssertionError(f"{dataset}: cantidad anómala incorrecta")
    for session in sessions:
        detected = detected_patterns(session.sequence)
        expected = (session.pattern,) if session.label == "anomala" else ()
        if detected != expected:
            raise AssertionError(f"{dataset}: etiqueta inconsistente en {session.session_id}")


def generate(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    datasets = {dataset: build_sessions(dataset) for dataset in TOTALS}
    for dataset, sessions in datasets.items():
        validate(sessions, dataset)

    validation_rows = rows_for_sessions(datasets["validation"], include_labels=True)
    test_rows = rows_for_sessions(datasets["test"], include_labels=False)
    validation_path = output_dir / "validacion.csv"
    test_path = output_dir / "prueba.csv"
    key_path = output_dir / "clave_prueba.csv"
    audit_path = output_dir / "auditoria_generacion.csv"
    write_csv(validation_path, validation_rows)
    write_csv(test_path, test_rows)
    write_key(key_path, datasets["test"])
    write_audit(audit_path, datasets)

    hashes = {
        "validacion.csv": sha256(validation_path),
        "prueba.csv": sha256(test_path),
        "clave_prueba.csv": sha256(key_path),
        "auditoria_generacion.csv": sha256(audit_path),
    }
    (output_dir / "hashes.sha256").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in hashes.items()),
        encoding="utf-8",
    )
    print(f"Validación: {len(datasets['validation'])} sesiones, {len(validation_rows)} eventos")
    print(f"Prueba: {len(datasets['test'])} sesiones, {len(test_rows)} eventos")
    print(f"SHA-256 validacion.csv: {hashes['validacion.csv']}")
    print(f"SHA-256 prueba.csv: {hashes['prueba.csv']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    generate(args.output_dir)
