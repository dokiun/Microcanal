#!/usr/bin/env python3
"""Calculate NuLocal from OpenFOAM sampling outputs.

The script uses the centreline temperature as Tb, as defined in NuLocal.md.
It accepts either CSV-like files with columns time,z,Tw,qWall or OpenFOAM
sampling files whose rows contain time followed by values.
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

DH = 2.0e-4
K_TABLE = ((300.0, 0.613), (373.15, 0.679))
DEFAULT_CASES = ("MicrocanalRe100V2", "MicrocanalRe400V2", "MicrocanalRe800V2")
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def conductivity(temperature: float) -> float:
    """Linearly interpolate liquid conductivity and clamp outside the table."""
    (t0, k0), (t1, k1) = K_TABLE
    if temperature <= t0:
        return k0
    if temperature >= t1:
        return k1
    return k0 + (temperature - t0) * (k1 - k0) / (t1 - t0)


def numbers(line: str) -> List[float]:
    return [float(value) for value in re.findall(NUMBER, line)]


def read_numeric_rows(path: Path) -> List[List[float]]:
    rows: List[List[float]] = []
    for line in path.read_text(errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        values = numbers(stripped.replace(",", " "))
        if values:
            rows.append(values)
    return rows


def find_file(case: Path, function_name: str, field_names: Tuple[str, ...]) -> Path:
    roots = [case / "postProcessing" / function_name]
    candidates: List[Path] = []
    for root in roots:
        if root.exists():
            for field_name in field_names:
                candidates.extend(root.rglob(field_name))
            candidates.extend(
                path for path in root.rglob("*") if path.is_file() and path.suffix in {".dat", ".csv"}
            )
    if not candidates:
        raise FileNotFoundError(
            f"No se encontró salida de {function_name} en {case / 'postProcessing'}"
        )
    return sorted(set(candidates))[0]


def read_centerline(path: Path, expected_points: int = 21) -> Dict[float, List[float]]:
    rows = read_numeric_rows(path)
    if not rows:
        raise ValueError(f"El archivo de probes está vacío: {path}")
    result: Dict[float, List[float]] = {}
    for row in rows:
        if len(row) < expected_points + 1:
            continue
        result[row[0]] = row[1 : expected_points + 1]
    if not result:
        raise ValueError(
            f"No se encontraron filas con {expected_points} valores de probes en {path}"
        )
    return result


def read_axial_wall(path: Path) -> Dict[float, List[Tuple[float, float]]]:
    """Read rows shaped as time,z,value or time,z,Tw,qWall.

    This deliberately requires an axial coordinate. A single patch average is
    not enough to calculate NuLocal(z).
    """
    rows = read_numeric_rows(path)
    result: Dict[float, List[Tuple[float, float]]] = {}
    for row in rows:
        if len(row) < 3:
            continue
        time = row[0]
        if len(row) == 3:
            result.setdefault(time, []).append((row[1], row[2]))
        else:
            result.setdefault(time, []).append((row[1], row[2]))
    if not result:
        raise ValueError(
            f"No se encontraron filas con formato tiempo,z,valor en {path}. "
            "Se necesita la posición axial para calcular NuLocal(z)."
        )
    return result


def interpolate(values: List[Tuple[float, float]], z: float) -> float:
    values = sorted(values)
    if z <= values[0][0]:
        return values[0][1]
    if z >= values[-1][0]:
        return values[-1][1]
    for (z0, v0), (z1, v1) in zip(values, values[1:]):
        if z0 <= z <= z1:
            fraction = (z - z0) / (z1 - z0)
            return v0 + fraction * (v1 - v0)
    raise ValueError(f"No se pudo interpolar z={z}")


def calculate_case(case: Path, output_root: Path) -> int:
    center_file = find_file(case, "centerlineTb", ("T.liquid", "T.liquid.dat"))
    wall_temperature = find_file(case, "wallTemperatureFluid", ("T.liquid", "T.liquid.dat"))
    wall_heat_flux = find_file(case, "wallHeatFluxFluid", ("wallHeatFlux.dat", "wallHeatFlux"))

    centerline = read_centerline(center_file)
    wall_t = read_axial_wall(wall_temperature)
    wall_q = read_axial_wall(wall_heat_flux)
    output_dir = output_root / case.name
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    output = output_dir / "NuLocal.dat"
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter=" ")
        writer.writerow(("time", "z", "Tb_center", "Tw", "qWall", "kLiquid", "hLocal", "NuLocal"))
        for time, temperatures in sorted(centerline.items()):
            for index, temperature in enumerate(temperatures):
                z = 0.005 * index / (len(temperatures) - 1)
                if time not in wall_t or time not in wall_q:
                    continue
                tw = interpolate(wall_t[time], z)
                q_wall = interpolate(wall_q[time], z)
                delta_t = tw - temperature
                if abs(delta_t) < 1.0e-12:
                    raise ValueError(f"Tw-Tb es cero en t={time}, z={z} para {case.name}")
                k_liquid = conductivity(temperature)
                h_local = q_wall / delta_t
                nu_local = h_local * DH / k_liquid
                writer.writerow(
                    (
                        f"{time:.12g}",
                        f"{z:.12g}",
                        f"{temperature:.12g}",
                        f"{tw:.12g}",
                        f"{q_wall:.12g}",
                        f"{k_liquid:.12g}",
                        f"{h_local:.12g}",
                        f"{nu_local:.12g}",
                    )
                )
                rows_written += 1
    return rows_written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", help="Casos a procesar (por defecto, los tres V2)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("postProcessing") / "NuLocal",
        help="Directorio de salida relativo a la raíz del proyecto",
    )
    args = parser.parse_args()
    root = Path.cwd()
    cases = [root / name for name in (args.cases or DEFAULT_CASES)]
    failures = 0
    for case in cases:
        try:
            count = calculate_case(case, args.output_dir)
            print(f"{case.name}: {count} filas escritas")
        except (FileNotFoundError, ValueError) as error:
            print(f"{case.name}: ERROR: {error}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
