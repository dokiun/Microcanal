#!/usr/bin/env python3
"""Muestra los resultados de un caso en un instante indicado en milisegundos."""

import argparse
import re

import numpy as np

from scripts.plot_results import PROJECT, load_case_data


def reductions(root):
    """Obtiene los nombres y regiones definidos en system/dataReduction."""
    source = (root / "system/dataReduction").read_text()
    source = re.sub(r"//[^\n]*|/\*.*?\*/", "", source, flags=re.S)
    for match in re.finditer(r"(?m)^(\w+)\s*\{([^{}]*)\}", source):
        name, body = match.groups()
        region = re.search(r"\bregion\s+(\w+)\s*;", body)
        if region:
            yield region.group(1), name


def read_reduction(root, region, name):
    """Lee columnas escalares y vectoriales usando el encabezado de OpenFOAM."""
    folder = root / "postProcessing" / region / name
    files = sorted(folder.glob("*/*.dat"))
    labels = None
    rows = {}
    for path in files:
        for line in path.read_text().splitlines():
            if line.startswith("# Time"):
                labels = [item.strip() for item in line[1:].split("\t")][1:]
            elif line.strip() and not line.startswith("#"):
                columns = re.findall(r"\([^()]*\)|\S+", line)
                time = float(columns[0])
                rows[time] = [tuple(float(x) for x in item[1:-1].split())
                              if item.startswith("(") else float(item)
                              for item in columns[1:]]
    return labels, rows


def format_value(label, values):
    unit = ""
    if re.search(r"\((?:T|T\.liquid|T\.gas)\)$", label):
        values = tuple(x - 273.15 for x in values)
        unit = " °C"
    elif re.search(r"\((?:p|p_rgh)\)$", label):
        unit = " Pa"
    elif re.search(r"\(U\.(?:liquid|gas)\)$", label):
        unit = " m/s"
    formatted = ", ".join(f"{x:.6g}" for x in values)
    return (f"({formatted})" if len(values) > 1 else formatted) + unit


def report_reductions(root, time_s):
    print("\nDatos de dataReduction:")
    for region, name in reductions(root):
        print(f"\n{region}/{name}:")
        labels, rows = read_reduction(root, region, name)
        if not labels or not rows:
            print("  sin datos")
            continue
        times = np.array(sorted(rows))
        if time_s < times[0] or time_s > times[-1]:
            print(f"  sin datos a este tiempo (disponible: {times[0] * 1e3:.6g}–{times[-1] * 1e3:.6g} ms)")
            continue
        before = times[np.searchsorted(times, time_s, side="right") - 1]
        after = times[min(np.searchsorted(times, time_s), len(times) - 1)]
        fraction = 0 if before == after else (time_s - before) / (after - before)
        for label, first, second in zip(labels, rows[before], rows[after]):
            a = np.atleast_1d(first)
            b = np.atleast_1d(second)
            values = a + fraction * (b - a)
            print(f"  {label}: {format_value(label, values)}")


def main():
    parser = argparse.ArgumentParser(
        description="Muestra las propiedades de postProcessing en un tiempo dado."
    )
    parser.add_argument("carpeta", help="Carpeta del caso dentro del proyecto")
    parser.add_argument("tiempo_ms", type=float, help="Tiempo solicitado en milisegundos")
    args = parser.parse_args()

    root = PROJECT / args.carpeta
    if root.resolve().parent != PROJECT or not root.is_dir():
        parser.error(f"Indica una carpeta existente dentro de {PROJECT}")

    data = load_case_data(root)
    times = data["time_ms"]
    t = args.tiempo_ms
    if not np.isfinite(t) or t < times[0] or t > times[-1]:
        parser.error(f"El tiempo debe estar entre {times[0]:.6g} y {times[-1]:.6g} ms")

    def value(key):
        return float(np.interp(t, times, data[key]))

    exact = np.any(np.isclose(times, t, rtol=0, atol=1e-9))
    print(f"Caso: {data['name']}")
    print(f"Tiempo: {t:.6g} ms ({'registro' if exact else 'interpolado'})")
    print(f"Caudal másico: {data['mdot']:.6g} kg/s")
    print(f"Flujo de calor en la base: {data['heat_flux']:.6g} W/m²")
    print(f"Caída de presión: {value('delta_p_pa'):.6g} Pa")
    print(f"Temperatura de la base: {value('t_base_k') - 273.15:.6g} °C")
    print(f"Temperatura de la pared: {value('t_wall_k') - 273.15:.6g} °C")
    print(f"Temperatura media del fluido: {value('t_fluid_k') - 273.15:.6g} °C")
    print(f"Coeficiente convectivo h: {value('h'):.6g} W/(m² K)")
    print(f"Número de Nusselt Nu: {value('nu'):.6g}")
    report_reductions(root, t / 1e3)


if __name__ == "__main__":
    main()
