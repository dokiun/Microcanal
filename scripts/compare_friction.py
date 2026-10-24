#!/usr/bin/env python3
"""Compara f_app·Re nominal y caída de presión del último registro de varios casos."""

import re
import os

import numpy as np
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
import matplotlib.pyplot as plt

from scripts.compare_cases import PLOTS, select_cases
from scripts.plot_results import foam_value, read_series


def parameter(root, key):
    path = root / f"{root.name}.dat"
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró {path}")
    return foam_value(path, rf"(?m)^\s*{re.escape(key)}\s+([\d.eE+-]+)\b", key)


def property_at_300(root, key):
    path = root / "constant/fluid/thermophysicalProperties.liquid"
    content = re.sub(r"//[^\n]*", "", path.read_text())
    match = re.search(rf"\b{key}\s*\((.*?)\)\s*;", content, re.S)
    if not match:
        raise ValueError(f"No se encontró la tabla {key} en {path}")
    pairs = [(float(t), float(v)) for t, v in re.findall(r"\(\s*([\d.eE+-]+)\s+([\d.eE+-]+)\s*\)", match.group(1))]
    if not pairs:
        raise ValueError(f"Tabla {key} vacía en {path}")
    pairs.sort()
    return float(np.interp(300.0, *map(np.array, zip(*pairs))))


def case_point(root):
    match = re.search(r"Re(\d+)(?!\d)", root.name, re.I)
    if not match:
        raise ValueError(f"No se encontró el Reynolds nominal en el nombre {root.name!r}")
    re_nominal = int(match.group(1))
    if re_nominal <= 0:
        raise ValueError(f"Reynolds nominal inválido en {root.name!r}")
    dh = parameter(root, "Dh_hidraulico")
    length = parameter(root, "L_total")
    area = parameter(root, "A_seccion_transversal")
    rho = property_at_300(root, "rho")
    mu = property_at_300(root, "mu")
    mdot = foam_value(root / "0/fluid/U.liquid", r"massFlowRate\s+constant\s+([\d.eE+-]+)\s*;", "massFlowRate")
    if min(dh, length, area, rho, mu, mdot) <= 0:
        raise ValueError("Geometría, propiedades y caudal deben ser positivos")

    inlet = read_series(root, "fluid", "inletFluid")
    outlet = read_series(root, "fluid", "outletFluid")
    # Se usa el último instante común para evitar extrapolar una presión.
    time = min(inlet[0][-1], outlet[0][-1])
    if time < max(inlet[0][0], outlet[0][0]):
        raise ValueError("Las series de presión no tienen tiempos superpuestos")
    p_in = np.interp(time, inlet[0], inlet[1][:, 0])
    p_out = np.interp(time, outlet[0], outlet[1][:, 0])
    delta_p = p_in - p_out
    u_hyd = mdot / (rho * area)
    reynolds = rho * u_hyd * dh / mu
    f_app = 2.0 * dh * delta_p / (length * rho * u_hyd**2)
    return root.name, re_nominal, f_app * re_nominal, delta_p, time, reynolds


def main():
    folders = select_cases()
    try:
        points = sorted((case_point(folder) for folder in folders), key=lambda point: point[1])
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"No se pudieron calcular los resultados: {error}") from error

    PLOTS.mkdir(exist_ok=True)
    for filename, ylabel, index in (
        ("comparacion_f_app_re.png", "f_app · Re nominal [–]", 2),
        ("comparacion_caida_presion_re.png", "Δp [Pa]", 3),
    ):
        fig, ax = plt.subplots(figsize=(9, 6), dpi=200)
        ax.plot([point[1] for point in points], [point[index] for point in points], "o-", linewidth=1.8)
        for point in points:
            ax.annotate(point[0], (point[1], point[index]), xytext=(5, 5), textcoords="offset points")
        ax.set_xlabel("Re nominal del caso [–]")
        ax.set_ylabel(ylabel)
        ax.grid(True, linestyle="--", alpha=0.5)
        fig.tight_layout()
        output = PLOTS / filename
        fig.savefig(output, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Gráfica: {output}")

    print("Caso                    Re nominal  Re calculado     f_app·Re       Δp [Pa]      tiempo [s]")
    for name, reynolds, product, delta_p, time, re_calculated in points:
        print(f"{name:24s} {reynolds:10d} {re_calculated:13.3f} {product:12.4f} {delta_p:13.3f} {time:15.6g}")


if __name__ == "__main__":
    main()
