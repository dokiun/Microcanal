#!/usr/bin/env python3
"""Compara f_app·Re nominal y caída de presión a un tiempo común."""

import argparse
import re
import os

import numpy as np
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
import matplotlib.pyplot as plt

if __package__:
    from .compare_cases import PLOTS, select_cases
    from .plot_results import foam_value, read_series
else:
    from compare_cases import PLOTS, select_cases
    from plot_results import foam_value, read_series


def parameter(root, *keys):
    path = root / f"{root.name}.dat"
    if not path.is_file():
        raise FileNotFoundError(f"No se encontró {path}")
    names = "|".join(re.escape(key) for key in keys)
    return foam_value(path, rf"(?m)^\s*(?:{names})\s+([\d.eE+-]+)\b", " o ".join(keys))


def property_at_300(root, key):
    path = root / "constant/fluid/thermophysicalProperties.liquid"
    if not path.is_file():
        path = root / "constant/fluid/thermophysicalProperties"
    content = re.sub(r"//[^\n]*", "", path.read_text())
    match = re.search(rf"\b{key}\s*\((.*?)\)\s*;", content, re.S)
    if not match:
        return foam_value(path, rf"\b{re.escape(key)}\s+([\d.eE+-]+)\s*;", key)
    pairs = [(float(t), float(v)) for t, v in re.findall(r"\(\s*([\d.eE+-]+)\s+([\d.eE+-]+)\s*\)", match.group(1))]
    if not pairs:
        raise ValueError(f"Tabla {key} vacía en {path}")
    pairs.sort()
    return float(np.interp(300.0, *map(np.array, zip(*pairs))))


def case_point(root, time):
    match = re.search(r"Re(\d+)(?!\d)", root.name, re.I)
    if not match:
        raise ValueError(f"No se encontró el Reynolds nominal en el nombre {root.name!r}")
    re_nominal = int(match.group(1))
    if re_nominal <= 0:
        raise ValueError(f"Reynolds nominal inválido en {root.name!r}")
    dh = parameter(root, "Dh_hidraulico", "Dh_canal_completo_m")
    length = parameter(root, "L_total", "Longitud_m")
    area = parameter(root, "A_seccion_transversal", "Area_entrada_total_m2")
    rho = property_at_300(root, "rho")
    mu = property_at_300(root, "mu")
    velocity = root / "0/fluid/U.liquid"
    if not velocity.is_file():
        velocity = root / "0/fluid/U"
    mdot = foam_value(velocity, r"massFlowRate\s+constant\s+([\d.eE+-]+)\s*;", "massFlowRate")
    if min(dh, length, area, rho, mu, mdot) <= 0:
        raise ValueError("Geometría, propiedades y caudal deben ser positivos")

    inlet = read_series(root, "fluid", "inletFluid")
    outlet = read_series(root, "fluid", "outletFluid")
    start = max(inlet[0][0], outlet[0][0])
    end = min(inlet[0][-1], outlet[0][-1])
    if not start <= time <= end:
        raise ValueError(f"{root.name}: {time * 1000:g} ms fuera del intervalo común "
                         f"[{start * 1000:g}, {end * 1000:g}] ms")
    p_in = np.interp(time, inlet[0], inlet[1][:, 0])
    p_out = np.interp(time, outlet[0], outlet[1][:, 0])
    delta_p = p_in - p_out
    u_hyd = mdot / (rho * area)
    reynolds = rho * u_hyd * dh / mu
    f_app = 2.0 * dh * delta_p / (length * rho * u_hyd**2)
    return root.name, re_nominal, f_app * re_nominal, delta_p, time, reynolds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time-ms", type=float, default=10.0,
                        help="Instante de comparación en milisegundos (predeterminado: 10)")
    parser.add_argument("carpetas", nargs="*")
    args = parser.parse_args()
    if not np.isfinite(args.time_ms) or args.time_ms < 0:
        parser.error("--time-ms debe ser un número finito no negativo")
    folders = select_cases(args.carpetas)
    time = args.time_ms / 1000.0
    try:
        points = sorted((case_point(folder, time) for folder in folders), key=lambda point: point[1])
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
        ax.set_title(f"Tiempo: {args.time_ms:g} ms")
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
