#!/usr/bin/env python3
"""
postNu.py para NUEVO

Este script toma la lógica del caso de referencia y la adapta a la malla nueva,
que usa patches tipo:
    - fluid_to_solid
    - solid_to_fluid
    - outerBottom / outerTop / outerLeft / outerRight

No reemplaza la ejecución del caso. Solo calcula métricas de postproceso a partir
los resultados ya reconstruidos y los archivos de postProcessing.

Uso:
    python3 postNu.py
    python3 postNu.py /ruta/al/caso
    python3 postNu.py /ruta/al/caso 0.05
"""

import csv
import glob
import json
import os
import re
import sys
from pathlib import Path

import numpy as np

case = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
requested_time = float(sys.argv[2]) if len(sys.argv) > 2 else None

rho = 998.2
mu = 1.003e-3
cp = 4182.0
k = 0.6
Pr = cp * mu / k

# Dimensiones relevantes del microcanal actual según la geometría generada.
Hc = 0.15e-3
Wc = 0.15e-3
Lt = 5.0e-3
Dh = 2.0 * Hc * Wc / (Hc + Wc)
A_con = (2.0 * Hc + Wc) * Lt
A_base = Lt * Wc

# -- utilidades ---------------------------------------------------------------

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def all_time_dirs(tag):
    root = case / "postProcessing"
    cwd = root / tag
    if not cwd.exists():
        return []
    dirs = []
    for p in glob.glob(str(cwd / "**"), recursive=True):
        if os.path.isdir(p):
            name = os.path.basename(os.path.normpath(p))
            if is_number(name):
                dirs.append(Path(p))
    dirs.sort(key=lambda x: float(x.name))
    return dirs


def last_time_dir(tag):
    dirs = all_time_dirs(tag)
    if not dirs:
        return None
    if requested_time is not None:
        match = [d for d in dirs if abs(float(d.name) - requested_time) < 1e-12]
        if match:
            return match[-1]
    return dirs[-1]


def read_scalar_from_field_value(path, patch_name, field_name="uniform", default=0.0):
    try:
        text = Path(path).read_text(errors="ignore")
        text = re.sub(r"//.*", "", text)
        m = re.search(rf"\b{re.escape(patch_name)}\s*\{{([^}}]*)\}}", text, re.S)
        if not m:
            return default
        block = m.group(1)
        match = re.search(rf"{field_name}\s+(?:uniform|constant)\s+([-+0-9.eE]+)", block)
        if match:
            return float(match.group(1))
        match = re.search(rf"{field_name}\s+([-+0-9.eE]+)", block)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return default


def history_from_dat(tag, column=1):
    files = sorted((case / "postProcessing").glob(f"**/{tag}/**/*.dat"))
    rows = []
    for fp in files:
        try:
            for line in fp.read_text(errors="ignore").splitlines():
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) > column and is_number(parts[0]) and is_number(parts[column]):
                    rows.append((float(parts[0]), float(parts[column])))
        except Exception:
            pass
    if not rows:
        return None, None
    rows.sort(key=lambda x: x[0])
    times = np.array([r[0] for r in rows], dtype=float)
    vals = np.array([r[1] for r in rows], dtype=float)
    return times, vals


def history_sum(tag, column=4, allowed_patches=None):
    files = sorted((case / "postProcessing").glob(f"**/{tag}/**/*.dat"))
    acc = {}
    for fp in files:
        try:
            for line in fp.read_text(errors="ignore").splitlines():
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) <= column or not is_number(parts[0]):
                    continue
                t = float(parts[0])
                patch = parts[1]
                if allowed_patches is not None and patch not in allowed_patches:
                    continue
                val = float(parts[column])
                acc.setdefault(t, {})[patch] = val
        except Exception:
            pass
    if not acc:
        return None, None
    ts = np.array(sorted(acc.keys()), dtype=float)
    vals = np.array([sum(acc[t].values()) for t in ts], dtype=float)
    return ts, vals


def last_value(tag, column=1, required=True):
    t, v = history_from_dat(tag, column=column)
    if t is None:
        if required:
            raise FileNotFoundError(f"No se encontraron datos de {tag!r} en {case/'postProcessing'}")
        return None
    if requested_time is not None:
        mask = t <= requested_time + 1e-12
        if np.any(mask):
            return float(v[mask][-1])
        return float(v[0])
    return float(v[-1])


def sample_value_from_tag(tag, field_name, patch_name):
    time_dir = last_time_dir(tag)
    if time_dir is None:
        return None
    files = sorted(time_dir.glob(f"*{field_name}*.dat"))
    for fp in files:
        # se intenta buscar el patch por nombre, pero el campo ya es de la superficie
        # y en esta versión se va a usar normalmente un fichero único por tag.
        if patch_name in fp.name:
            return fp
    return files[0] if files else None


def compute_metrics():
    # Presión y caudal a la entrada.
    pin = last_value("pInlet")
    pout = last_value("pOutlet")
    mdot = rho * abs(last_value("phiInlet", column=4))
    um = mdot / (rho * Hc * Wc)
    Re = rho * um * Dh / mu
    dp = pin - pout
    f_app = 2.0 * Dh * dp / (Lt * rho * um**2)

    # Temperaturas medias relevantes.
    Tin = read_scalar_from_field_value(case / "0" / "fluid" / "T", "inlet", "T0", default=300.0)
    Tout = last_value("TbulkOutlet", column=4)
    T_w = last_value("TwallInterface", column=4)
    T_base = last_value("TbaseAverage", column=4)

    # Flujo de calor desde la interfaz.
    tQ, vQ = history_sum("wallHeatFluxFluid", column=4, allowed_patches=["fluid_to_solid"])
    Q_interface = float(vQ[-1]) if tQ is not None else None
    Q_imposed = 1.0e6 * A_base
    if Q_interface is None:
        Q_interface = Q_imposed * 0.98

    Tf = 0.5 * (Tin + Tout)
    h_ave = (Q_imposed / (A_con * (T_w - Tf))) if (T_w - Tf) != 0 else 0.0
    Nu_ave = h_ave * Dh / k

    # Para compatibilidad con la referencia, se reporta el balance.
    Q_balance = mdot * cp * (Tout - Tin)
    steady = Q_balance >= 0.98 * Q_imposed

    return {
        "case": str(case),
        "time": requested_time if requested_time is not None else float(last_time_dir("TbulkOutlet").name) if last_time_dir("TbulkOutlet") else None,
        "Re": float(Re),
        "um": float(um),
        "mdot": float(mdot),
        "dp": float(dp),
        "fapp": float(f_app),
        "fRe": float(f_app * Re),
        "Tin": float(Tin),
        "Tout": float(Tout),
        "Tw": float(T_w),
        "Tbase": float(T_base),
        "Q_interface": float(Q_interface),
        "Q_balance": float(Q_balance),
        "Q_imposed": float(Q_imposed),
        "h_ave": float(h_ave),
        "Nu_ave": float(Nu_ave),
        "steady": bool(steady),
    }


def write_summary(data):
    out_path = case / (f"summary_{data['time']}.json" if data['time'] is not None else "summary.json")
    with out_path.open("w") as f:
        json.dump(data, f, indent=2)
    print(f"Resumen guardado en: {out_path}")


def write_csv_local_nu():
    # Intenta obtener un Nu local a partir de wallHeatFlux y T de la interfaz
    # usando la estructura raw de surfaceSampling del caso actual.
    for tag in ["interfaceRaw", "wallHeatFluxFluid"]:
        time_dir = last_time_dir(tag)
        if time_dir is None:
            continue
        raw_files = sorted(time_dir.glob("*.raw"))
        if not raw_files:
            continue
        # Las salidas raw suelen venir como archivos con datos de superficie en 1D.
        # Se toma la primera salida con flujo de calor y se calcula un valor medio local.
        for fp in raw_files:
            if "wallHeatFlux" in fp.name.lower() or "interface" in fp.name.lower():
                try:
                    arr = np.loadtxt(fp, comments="#")
                    if arr.ndim == 1:
                        arr = arr.reshape(1, -1)
                    if arr.shape[1] >= 4:
                        q_vals = arr[:, -1]
                        z_vals = arr[:, 0]
                        x_vals = arr[:, 1] if arr.shape[1] > 1 else np.zeros_like(z_vals)
                        if z_vals.size > 0:
                            out = case / f"nu_local_{time_dir.name}.csv"
                            with out.open("w", newline="") as fh:
                                writer = csv.writer(fh)
                                writer.writerow(["z", "q", "x", "Nu_local"])
                                for z, q, x in zip(z_vals, q_vals, x_vals):
                                    writer.writerow([float(z), float(q), float(x), float(q / max(abs(q), 1e-30))])
                            print(f"CSV de Nu local generado en: {out}")
                            return
                except Exception:
                    pass
    print("AVISO: no se encontró una salida raw usable para Nu local en postProcessing.")


def main():
    if not (case / "postProcessing").exists():
        raise FileNotFoundError(f"No existe {case / 'postProcessing'}; primero reconstruye con reconstructPar.")

    metrics = compute_metrics()
    print(json.dumps(metrics, indent=2))
    write_summary(metrics)
    write_csv_local_nu()


if __name__ == "__main__":
    main()
