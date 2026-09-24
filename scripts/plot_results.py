#!/usr/bin/env python3
"""
Script de procesamiento y graficación de resultados de simulación CFD en microcanales.
Calcula y grafica las magnitudes del artículo Ghani et al. (2017):
- Caída de presión ΔP(t) y Factor de fricción aparente f_app(t) (Ec. 10 y 18).
- Temperatura promedio de la base caliente T_base(t) (Fig. 10).
- Coeficiente convectivo h_ave(t) y Número de Nusselt Nu_ave(t) (Ecs. 11 y 12).
- Fracción de vapor alpha_gas(t).
"""
from pathlib import Path
import re
import numpy as np
import os

# Set writable cache dir for matplotlib
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib-cache'

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
POST_DIR = ROOT / "postProcessing"
PLOTS_DIR = ROOT / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

# Geometric and physical parameters (MC-RC Ghani et al., 2017)
DH = 200e-6        # Diámetro hidráulico (200 µm = 0.0002 m)
LT = 10e-3         # Longitud del canal (10 mm = 0.010 m)
A_BASE = 3.0e-6    # Área de la base caliente (0.3 mm x 10 mm = 3e-6 m²)
A_CONV = 9.0e-6    # Área convectiva mojada nominal (2 x (0.075 + 0.30 + 0.075) mm x 10 mm = 9e-6 m²)
Q_FLUX = 1.0e6     # Flujo de calor en la base (100 W/cm² = 1e6 W/m²)
RHO_FLUID = 958.4  # Densidad de referencia del fluido (kg/m³)
K_FLUID = 0.671    # Conductividad térmica del fluido (W/(m K))
CP_FLUID = 4216.0  # Calor específico del fluido (J/(kg K))
MDOT = 1.21e-5     # Caudal másico total en inlet (kg/s)
A_INLET = 4.5e-8   # Área de entrada total (4.5e-8 m²)
U_MEAN = MDOT / (RHO_FLUID * A_INLET) # ~0.2805 m/s
RE_DH = RHO_FLUID * U_MEAN * DH / 2.8176e-4  # Re_Dh con mu del thermophysicalProperties.liquid

def load_dat_file(file_path):
    """Lee un archivo .dat de OpenFOAM y extrae encabezados y datos numéricos."""
    if not file_path.exists():
        return None, None
    lines = file_path.read_text().splitlines()
    header_line = None
    data_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('# Time') or line.startswith('#Time') or ('Time' in line and line.startswith('#')):
            header_line = line.lstrip('#').strip().split()
        elif not line.startswith('#'):
            # Parse row handling vector components like (0 0 0.28)
            clean_row = re.sub(r'[\(\)]', ' ', line)
            parts = [float(x) for x in clean_row.split()]
            if parts:
                data_lines.append(parts)
                
    if not data_lines:
        return header_line, None
    return header_line, np.array(data_lines)

def find_latest_dat(subpath):
    """Encuentra todos los archivos .dat de una serie temporal concatenando si hubo reinicios."""
    target_dir = POST_DIR / subpath
    if not target_dir.exists():
        return None, None
    
    time_dirs = sorted([d for d in target_dir.iterdir() if d.is_dir()], key=lambda p: float(p.name) if p.name.replace('.','',1).isdigit() else -1)
    if not time_dirs:
        return None, None
    
    all_data = []
    header = None
    for td in time_dirs:
        for f in td.glob('*.dat'):
            h, d = load_dat_file(f)
            if h is not None:
                header = h
            if d is not None:
                all_data.append(d)
                
    if not all_data:
        return header, None
    
    combined = np.vstack(all_data)
    # Sort by time and drop duplicates
    combined = combined[np.argsort(combined[:, 0])]
    _, unique_indices = np.unique(combined[:, 0], return_index=True)
    return header, combined[unique_indices]

def main():
    print("=" * 70)
    print("PROCESAMIENTO DE RESULTADOS CFD — MICROCANAL MC-RC (Ghani et al., 2017)")
    print("=" * 70)

    # 1. Cargar datos
    h_in, d_in = find_latest_dat("fluid/inletFluid")
    h_out, d_out = find_latest_dat("fluid/outletFluid")
    h_base, d_base = find_latest_dat("solid/baseSolid")
    h_int_f, d_int_f = find_latest_dat("fluid/interfaceFluid")
    h_int_s, d_int_s = find_latest_dat("solid/interfaceSolid")
    h_vol, d_vol = find_latest_dat("fluid/volFluid")

    if d_in is None or d_base is None:
        print("No se encontraron suficientes datos en postProcessing/. Ejecuta la simulación primero con AllrunCh.")
        return

    # Sincronizar tiempos comunes
    times = d_in[:, 0]
    
    # 2. Variables Hidráulicas (Presión y Fricción)
    # inlet: [Time, p, p_rgh, T.liquid, alpha.gas, Ux, Uy, Uz]
    # outlet: [Time, p, p_rgh, T.liquid, T.gas, alpha.gas, Ux, Uy, Uz, U_gx, U_gy, U_gz]
    p_in = d_in[:, 1]
    p_out = d_out[:, 1] if d_out is not None else np.zeros_like(p_in)
    delta_p = p_in - p_out  # Pa
    delta_p_kpa = delta_p / 1000.0
    f_app = (2.0 * DH * delta_p) / (LT * RHO_FLUID * (U_MEAN**2))

    # 3. Variables Térmicas
    # baseSolid: [Time, T]
    t_base = d_base[:, 1]
    t_base_c = t_base - 273.15

    # interface: [Time, T]
    t_wall = d_int_s[:, 1] if d_int_s is not None else (d_int_f[:, 1] if d_int_f is not None else t_base)
    t_wall_c = t_wall - 273.15

    # volFluid: [Time, T.liquid, T.gas, alpha.gas, p]
    t_fluid = d_vol[:, 1] if d_vol is not None else (d_in[:, 3] + d_out[:, 3]) / 2.0
    t_fluid_c = t_fluid - 273.15

    # 4. Coeficiente convectivo y Nusselt (Ecs. 11 y 12)
    # hav e = (qw * Afilm) / (Aconv * (Tw,ave - Tf,ave))
    # Nuave = have * Dh / kf
    delta_t_conv = np.maximum(t_wall - t_fluid, 1e-4)
    h_ave = (Q_FLUX * A_BASE) / (A_CONV * delta_t_conv)
    nu_ave = (h_ave * DH) / K_FLUID

    # 5. Fracción de vapor
    alpha_gas = d_vol[:, 3] if d_vol is not None else np.zeros_like(times)

    # Imprimir resumen del último estado
    last_idx = -1
    print(f"\n--- ÚLTIMO ESTADO REGISTRADO (t = {times[last_idx]:.6e} s) ---")
    print(f"• Caída de presión (ΔP)     : {delta_p[last_idx]:.2f} Pa ({delta_p_kpa[last_idx]:.4f} kPa)")
    print(f"• Factor de fricción (f_app) : {f_app[last_idx]:.5f}")
    print(f"• Temp. Base Caliente (T_base): {t_base[last_idx]:.2f} K ({t_base_c[last_idx]:.2f} °C)")
    print(f"• Temp. Pared Mojada (T_w)   : {t_wall[last_idx]:.2f} K ({t_wall_c[last_idx]:.2f} °C)")
    print(f"• Temp. Media Fluido (T_f)   : {t_fluid[last_idx]:.2f} K ({t_fluid_c[last_idx]:.2f} °C)")
    print(f"• Coeficiente Convectivo (h) : {h_ave[last_idx]:.2f} W/(m² K)")
    print(f"• Número de Nusselt (Nu_ave) : {nu_ave[last_idx]:.3f}")
    print(f"• Fracción media de vapor    : {alpha_gas[last_idx]:.4e}")
    print(f"• Número de Reynolds (Re_Dh) : {RE_DH:.2f} (laminar)")

    # =========================================================================
    # GENERACIÓN DE GRÁFICAS (ESTILO PAPER ACADÉMICO / ELSEVIER)
    # =========================================================================
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    fig, axs = plt.subplots(2, 2, figsize=(12, 9), dpi=200)

    # Subplot 1: Temperaturas
    ax1 = axs[0, 0]
    ax1.plot(times * 1e3, t_base_c, label=r'Base Caliente $T_{\mathrm{base}}$ (Fig. 10)', color='#dc2626', lw=2)
    ax1.plot(times * 1e3, t_wall_c, label=r'Pared Canal $T_{W,\mathrm{ave}}$', color='#d97706', lw=1.8, ls='--')
    ax1.plot(times * 1e3, t_fluid_c, label=r'Fluido Medio $T_{f,\mathrm{ave}}$', color='#2563eb', lw=1.8, ls=':')
    ax1.set_xlabel('Tiempo $t$ [ms]', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Temperatura [°C]', fontsize=11, fontweight='bold')
    ax1.set_title('(a) Evolución Térmica del Microcanal', fontsize=12, fontweight='bold')
    ax1.legend(loc='best', frameon=True, fontsize=10)
    ax1.grid(True, linestyle='--', alpha=0.6)

    # Subplot 2: Caída de presión y Factor de Fricción
    ax2 = axs[0, 1]
    color_p = '#059669'
    ax2.plot(times * 1e3, delta_p_kpa, color=color_p, lw=2, label=r'$\Delta P$ [kPa]')
    ax2.set_xlabel('Tiempo $t$ [ms]', fontsize=11, fontweight='bold')
    ax2.set_ylabel(r'Caída de Presión $\Delta P$ [kPa]', color=color_p, fontsize=11, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color_p)
    ax2.grid(True, linestyle='--', alpha=0.6)

    # Eje secundario para f_app
    ax2_twin = ax2.twinx()
    color_f = '#7c3aed'
    ax2_twin.plot(times * 1e3, f_app, color=color_f, lw=1.8, ls='--', label=r'$f_{\mathrm{app}}$')
    ax2_twin.set_ylabel(r'Factor de Fricción Aparente $f_{\mathrm{app}}$', color=color_f, fontsize=11, fontweight='bold')
    ax2_twin.tick_params(axis='y', labelcolor=color_f)
    ax2.set_title('(b) Comportamiento Hidráulico (Ecs. 10 y 18)', fontsize=12, fontweight='bold')

    # Subplot 3: Nusselt y Coeficiente de Transferencia de Calor
    ax3 = axs[1, 0]
    color_nu = '#2563eb'
    ax3.plot(times * 1e3, nu_ave, color=color_nu, lw=2, label=r'$\mathrm{Nu}_{\mathrm{ave}}$')
    ax3.set_xlabel('Tiempo $t$ [ms]', fontsize=11, fontweight='bold')
    ax3.set_ylabel(r'Número de Nusselt $\mathrm{Nu}_{\mathrm{ave}}$', color=color_nu, fontsize=11, fontweight='bold')
    ax3.tick_params(axis='y', labelcolor=color_nu)
    ax3.grid(True, linestyle='--', alpha=0.6)

    ax3_twin = ax3.twinx()
    color_h = '#ea580c'
    ax3_twin.plot(times * 1e3, h_ave, color=color_h, lw=1.8, ls='-.', label=r'$h_{\mathrm{ave}}$')
    ax3_twin.set_ylabel(r'Coeficiente Convectivo $h_{\mathrm{ave}}$ [$\mathrm{W/(m^2 K)}$]', color=color_h, fontsize=11, fontweight='bold')
    ax3_twin.tick_params(axis='y', labelcolor=color_h)
    ax3.set_title('(c) Transferencia de Calor (Ecs. 11 y 12)', fontsize=12, fontweight='bold')

    # Subplot 4: Fracción de Vapor
    ax4 = axs[1, 1]
    ax4.plot(times * 1e3, alpha_gas * 100, color='#9333ea', lw=2, label=r'$\alpha_{\mathrm{gas}}$ volumétrico')
    ax4.set_xlabel('Tiempo $t$ [ms]', fontsize=11, fontweight='bold')
    ax4.set_ylabel(r'Fracción de Vapor $\alpha_{\mathrm{gas}}$ [%]', fontsize=11, fontweight='bold')
    ax4.set_title('(d) Fracción de Fase Gaseosa (Cambio de Fase)', fontsize=12, fontweight='bold')
    ax4.grid(True, linestyle='--', alpha=0.6)
    ax4.legend(loc='best', frameon=True, fontsize=10)

    fig.suptitle(f'Resultados CFD — Microcanal MC-RC (Ghani et al., 2017) — Re_Dh = {RE_DH:.1f}', fontsize=14, fontweight='bold', y=0.99)
    plt.tight_layout()

    out_png = PLOTS_DIR / "resultados_ghani_mcrc.png"
    out_pdf = PLOTS_DIR / "resultados_ghani_mcrc.pdf"
    plt.savefig(out_png, dpi=300)
    plt.savefig(out_pdf)
    print(f"\n Gráfica guardada exitosamente en:")
    print(f"  • Imagen PNG: {out_png}")
    print(f"  • Vectorial PDF: {out_pdf}")

if __name__ == "__main__":
    main()
