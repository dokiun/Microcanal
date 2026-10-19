# Cambios y configuración — MicrocanalRe400V1

**Fecha de corte:** 2026-10-19

## Resumen

Caso de flujo laminar de agua en un microcanal de silicio, resuelto con `chtMultiRegionTwoPhaseEulerFoam`.

- Caso nominal: **Re ≈ 400**.
- Velocidad inicial en `0/fluid/U.liquid`: **1.7090763 m/s**.
- Caudal másico impuesto: **1.0236 × 10⁻⁴ kg/s**.
- Temperatura de entrada: **300 K**.
- Flujo de calor en la base: **10⁶ W/m²**.
- Presión de salida: **101325 Pa**.

## Geometría y malla

- Dominio: **0.30 × 0.40 × 5 mm**.
- Diámetro hidráulico: **200 µm**.
- Regiones: `fluid` y `solid`.
- Geometría de entrada: `geometry/Microcanal.stl`.
- Malla base: **32 × 32 × 80 = 81 920 celdas**.
- Mallado: `AllmeshSTL`, con `blockMesh`, `snappyHexMesh`, `topoSet` y `splitMeshRegions`.

## Ejecución

```bash
bash AllmeshSTL
bash Allrun
```

En clúster:

```bash
sbatch run_hpc.slurm
```

Verificación:

```bash
checkMesh -constant -region fluid
checkMesh -constant -region solid
python3 scripts/check_euler.py
```

## Resultados

El caso registra variables térmicas e hidráulicas en `postProcessing/`, incluyendo caída de presión, temperaturas medias y `ReDh`. Los archivos `processor*/`, `postProcessing/` y logs son resultados generados y quedan excluidos por el `.gitignore` raíz.

