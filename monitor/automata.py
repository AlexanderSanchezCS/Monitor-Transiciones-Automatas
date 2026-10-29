"""Definición y operaciones del autómata del monitor."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


ALPHABET = ("B", "P", "F", "C", "X", "D", "R", "V")
STATES = ("M0", "M1", "M2", "M3")
INITIAL_STATE = "M0"
ACCEPTING_STATES = frozenset({"M3"})

AUTOMATON_STATES = [
    {"id": "M0", "name": "Inicio", "description": "Estado inicial; aún no se ha detectado una anomalía."},
    {"id": "M1", "name": "Coincidencia parcial", "description": "Recuerda una posible coincidencia parcial de los patrones BC o CC."},
    {"id": "M2", "name": "Recorrido sin coincidencia", "description": "Estado de recorrido sin coincidencias parciales activas."},
    {"id": "M3", "name": "Aceptación", "description": "La cadena pertenece a uno de los lenguajes anómalos."},
]

TRANSITIONS = {
    "M0": {"B": "M1", "P": "M2", "F": "M2", "C": "M1", "X": "M2", "D": "M3", "R": "M3", "V": "M2"},
    "M1": {"B": "M1", "P": "M2", "F": "M2", "C": "M3", "X": "M2", "D": "M2", "R": "M2", "V": "M2"},
    "M2": {"B": "M1", "P": "M2", "F": "M2", "C": "M1", "X": "M2", "D": "M2", "R": "M2", "V": "M2"},
    "M3": {"B": "M3", "P": "M3", "F": "M3", "C": "M3", "X": "M3", "D": "M3", "R": "M3", "V": "M3"},
}


def validate_sequence(sequence: str) -> str:
    normalized = sequence.strip().upper()
    invalid = sorted(set(normalized) - set(ALPHABET))
    if not normalized:
        raise ValueError("La secuencia no puede estar vacía.")
    if invalid:
        raise ValueError(f"Símbolos inválidos: {', '.join(invalid)}.")
    return normalized


def simulate(sequence: str) -> list[dict[str, str]]:
    normalized = validate_sequence(sequence)
    state = INITIAL_STATE
    trace = [{"from": "—", "symbol": "Inicio", "to": state}]
    for symbol in normalized:
        next_state = TRANSITIONS[state][symbol]
        trace.append({"from": state, "symbol": symbol, "to": next_state})
        state = next_state
    return trace


def accepts(sequence: str) -> bool:
    return simulate(sequence)[-1]["to"] in ACCEPTING_STATES


def epsilon_closure(states: Iterable[str], epsilon: dict[str, Iterable[str]]) -> frozenset[str]:
    """Calcula el cierre-ε de un conjunto de estados."""
    closure = set(states)
    pending = list(closure)
    while pending:
        state = pending.pop()
        for target in epsilon.get(state, ()):
            if target not in closure:
                closure.add(target)
                pending.append(target)
    return frozenset(closure)


def subset_construction(
    states: Iterable[str],
    alphabet: Iterable[str],
    transitions: dict[str, dict[str, Iterable[str]]],
    initial: Iterable[str],
    accepting: Iterable[str],
    epsilon: dict[str, Iterable[str]] | None = None,
) -> dict[str, object]:
    """Convierte un AFN (con ε opcionales) a un AFD mediante subconjuntos."""
    epsilon = epsilon or {}
    alphabet = tuple(alphabet)
    accepting = set(accepting)
    start = epsilon_closure(initial, epsilon)
    names = {start: "S0"}
    pending = [start]
    deterministic: dict[str, dict[str, str]] = {}
    while pending:
        current = pending.pop(0)
        name = names[current]
        deterministic[name] = {}
        for symbol in alphabet:
            reached = {
                target
                for state in current
                for target in transitions.get(state, {}).get(symbol, ())
            }
            target_set = epsilon_closure(reached, epsilon)
            if target_set not in names:
                names[target_set] = f"S{len(names)}"
                pending.append(target_set)
            deterministic[name][symbol] = names[target_set]
    final = [name for subset, name in names.items() if subset & accepting]
    return {"states": list(names.values()), "initial": "S0", "accepting": final, "transitions": deterministic}


def minimize_dfa(
    states: Iterable[str],
    alphabet: Iterable[str],
    transitions: dict[str, dict[str, str]],
    initial: str,
    accepting: Iterable[str],
) -> dict[str, object]:
    """Minimiza un AFD con refinamiento iterativo de particiones."""
    states = frozenset(states)
    alphabet = tuple(alphabet)
    accepting = frozenset(accepting)
    partitions = [accepting, states - accepting]
    partitions = [part for part in partitions if part]
    changed = True
    while changed:
        changed = False
        groups = {state: index for index, part in enumerate(partitions) for state in part}
        refined = []
        for part in partitions:
            buckets: dict[tuple[int, ...], set[str]] = defaultdict(set)
            for state in part:
                signature = tuple(groups[transitions[state][symbol]] for symbol in alphabet)
                buckets[signature].add(state)
            refined.extend(buckets.values())
            changed |= len(buckets) > 1
        partitions = refined
    names = {state: f"M{index}" for index, part in enumerate(partitions) for state in part}
    return {
        "states": list(names.values()),
        "initial": names[initial],
        "accepting": sorted({names[state] for state in accepting}),
        "transitions": {
            names[next(iter(part))]: {
                symbol: names[transitions[next(iter(part))][symbol]] for symbol in alphabet
            }
            for part in partitions
        },
    }

