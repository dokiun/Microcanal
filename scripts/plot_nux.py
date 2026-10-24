#!/usr/bin/env python3
"""Calcula y grafica Nu_x según las ecuaciones (13) y (14)."""

import argparse
import csv
import os
import re

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
import matplotlib.pyplot as plt
import numpy as np

from scripts.compare_cases import PLOTS, case_folder
from scripts.compare_friction import parameter, property_at_300
from scripts.plot_results import foam_value


def nux(x, dh, reynolds, prandtl):
    X = x / (dh * reynolds * prandtl)
    return 1.0958 * (23.315 + 27038 * X + 1783300 * X**2) / (
        1 + 3049 * X + 472520 * X**2 - 35714 * X**3
    )


def case_data(folder, re_source, points):
    dh = parameter(folder, "Dh_hidraulico")
    length = parameter(folder, "L_total")
    area = parameter(folder, "A_seccion_transversal")
    rho = property_at_300(folder, "rho")
    mu = property_at_300(folder, "mu")
    cp = property_at_300(folder, "Cp")
    kappa = property_at_300(folder, "kappa")
    mdot = foam_value(folder / "0/fluid/U.liquid",
                      r"massFlowRate\s+constant\s+([\d.eE+-]+)\s*;", "massFlowRate")
    if min(dh, length, area, rho, mu, cp, kappa, mdot) <= 0:
        raise ValueError(f"Parámetros físicos no positivos en {folder.name}")
    re_calculated = mdot * dh / (area * mu)
    if re_source == "nominal":
        match = re.search(r"Re(\d+)(?!\d)", folder.name, re.I)
        if not match or int(match.group(1)) <= 0:
            raise ValueError(f"No se encontró Re nominal en {folder.name}")
        reynolds = int(match.group(1))
    else:
        reynolds = re_calculated
    prandtl = mu * cp / kappa
    x = np.linspace(0, length, points)
    return x, nux(x, dh, reynolds, prandtl), dh, reynolds, re_calculated, prandtl


def main():
    parser = argparse.ArgumentParser(description="Grafica Nu_x a lo largo de uno o varios microcanales")
    parser.add_argument("carpetas", nargs="+", help="Carpetas de casos dentro del proyecto")
    parser.add_argument("--re", choices=("calculado", "nominal"), default="nominal",
                        help="Re del nombre del caso (predeterminado) o del caudal impuesto")
    parser.add_argument("--puntos", type=int, default=201, help="Número de posiciones x (mínimo 2)")
    args = parser.parse_args()
    if args.puntos < 2:
        parser.error("--puntos debe ser al menos 2")
    if len(set(args.carpetas)) != len(args.carpetas):
        parser.error("Cada caso debe aparecer una sola vez")
    try:
        folders = [case_folder(name) for name in args.carpetas]
        data = [(folder.name, *case_data(folder, args.re, args.puntos)) for folder in folders]
    except (FileNotFoundError, ValueError) as error:
        parser.error(str(error))

    PLOTS.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 6), dpi=200)
    for name, x, nu, dh, reynolds, re_calculated, prandtl in data:
        X = x / (dh * reynolds * prandtl)
        ax.plot(X, nu, label=f"{name} (Re={reynolds:.1f})", linewidth=1.8)
        output = PLOTS / f"nux_{name}_{args.re}.csv"
        with output.open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("x_m", "X", "Nu_x", "Re_usado", "Pr"))
            writer.writerows((position, scaled, value, reynolds, prandtl)
                             for position, scaled, value in zip(x, X, nu))
        print(f"{name}: Re usado={reynolds:.3f}; Re por caudal={re_calculated:.3f}; Pr={prandtl:.4f}; CSV: {output}")
    ax.set_xlabel("X = x / (Dₕ Re Pr) [–]")
    ax.set_ylabel("Nuₓ [–]")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    output = PLOTS / f"comparacion_nux_{args.re}.png"
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Gráfica: {output}")


if __name__ == "__main__":
    main()
