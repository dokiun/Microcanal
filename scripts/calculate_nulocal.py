#!/usr/bin/env python3
"""Calcula NuLocal de V3 con Tb central y flujo de pared uniforme supuesto."""

import argparse
import bisect
import csv
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
import matplotlib.pyplot as plt

DH = 2.0e-4
K_TABLE = ((300.0, 0.613), (373.15, 0.679))
DEFAULT_CASES = ("MicrocanalRe100V3", "MicrocanalRe400V3", "MicrocanalRe800V3")
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


def read_uniform_flux(case: Path) -> Tuple[List[float], List[float]]:
    """Flujo medio hacia el fluido: -integral(solid_to_fluid) / área."""
    folder = case / "postProcessing" / "solid" / "wallHeatFluxFluid"
    files = list(folder.glob("*/*.dat"))
    if not files:
        raise FileNotFoundError(f"No se encontró wallHeatFluxFluid en {folder}")
    path = max(files, key=lambda file: file.stat().st_size)
    area_file = case / "postProcessing" / "solid" / "interfaceSolid" / "0" / "surfaceFieldValue_0.dat"
    if not area_file.is_file():
        area_file = case / "postProcessing" / "solid" / "interfaceSolid" / "0" / "surfaceFieldValue.dat"
    match = re.search(r"^# Area\s*:\s*(" + NUMBER + r")", area_file.read_text(), re.M)
    if not match or float(match.group(1)) <= 0:
        raise ValueError(f"Área de interfaz no válida en {area_file}")
    area = float(match.group(1))
    rows = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1] == "solid_to_fluid":
            rows[float(parts[0])] = -float(parts[4]) / area
    if not rows:
        raise ValueError(f"Sin flujo integral en {path}")
    times = sorted(rows)
    return times, [rows[time] for time in times]


def flux_at(time: float, times: List[float], fluxes: List[float]) -> float:
    if not times[0] <= time <= times[-1]:
        raise ValueError(f"Flujo de pared no disponible en t={time}")
    index = bisect.bisect_left(times, time)
    if index < len(times) and times[index] == time:
        return fluxes[index]
    t0, t1 = times[index - 1], times[index]
    return fluxes[index - 1] + (fluxes[index] - fluxes[index - 1]) * (time - t0) / (t1 - t0)


def calculate_case(case: Path) -> int:
    v3_center = case / "postProcessing" / "centerlineTb" / "fluid" / "0" / "T"
    if not v3_center.is_file():
        raise FileNotFoundError(f"No se encontró {v3_center}")
    centerline = read_centerline(v3_center)
    wall_file = case / "postProcessing" / "wallTemperatureFluid" / "fluid" / "0" / "T"
    wall_temperatures = read_centerline(wall_file)
    flux_times, flux_values = read_uniform_flux(case)
    output_dir = case / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    profiles = {}
    output = output_dir / "NuLocal.dat"
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter=" ")
        stream.write("# qWall uniforme supuesto: -integral(wallHeatFluxFluid)/area(interfaceSolid)\n")
        writer.writerow(("time", "z", "Tb_center", "Tw", "qWall_uniform", "kLiquid", "hLocal_uniform", "NuLocal_uniform"))
        for time, temperatures in sorted(centerline.items()):
            if time not in wall_temperatures:
                continue
            q_wall = flux_at(time, flux_times, flux_values)
            profiles[time] = ([], [])
            for index, temperature in enumerate(temperatures):
                z = 0.005 * index / (len(temperatures) - 1)
                tw = wall_temperatures[time][index]
                delta_t = tw - temperature
                if abs(delta_t) < 1.0e-12:
                    raise ValueError(f"Tw-Tb es cero en t={time}, z={z} para {case.name}")
                k_liquid = conductivity(temperature)
                h_local = q_wall / delta_t
                nu_local = h_local * DH / k_liquid
                profiles[time][0].append(z * 1000)
                profiles[time][1].append(nu_local)
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
    if not rows_written:
        output.unlink()
        raise ValueError(f"No hay tiempos comunes de temperatura para {case.name}")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(9, 6), dpi=200)
    time = max(profiles)
    z_mm, nu_values = profiles[time]
    ax.plot(z_mm, nu_values, marker="o", markersize=3)
    ax.set_xlabel("Posición axial z [mm]")
    ax.set_ylabel("Nu local [–]")
    ax.set_title(f"{case.name} — t = {time * 1000:.2f} ms, flujo uniforme supuesto")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    figure = output_dir / "NuLocal.png"
    fig.savefig(figure, dpi=300)
    plt.close(fig)
    print(f"Gráfica: {figure}")
    return rows_written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", help="Casos a procesar (por defecto, los tres V3)")
    args = parser.parse_args()
    root = Path.cwd()
    cases = [root / name for name in (args.cases or DEFAULT_CASES)]
    failures = 0
    for case in cases:
        try:
            count = calculate_case(case)
            print(f"{case.name}: {count} filas escritas")
        except (FileNotFoundError, ValueError) as error:
            print(f"{case.name}: ERROR: {error}", file=sys.stderr)
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
