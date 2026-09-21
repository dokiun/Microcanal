# Microcanal: geometría y malla

Mallado multirregión desde `geometry/Microcanal.stl`, en milímetros. El STL representa un sólido con sección en I; el fluido ocupa los dos canales laterales.

- Dimensiones exteriores: **0.30 × 0.40 × 10 mm**.
- Cada canal: **0.075 × 0.30 × 10 mm**.
- Regiones: `solid` y `fluid` (ambos canales).

## Generar la malla

Con OpenFOAM y Python 3 disponibles, ejecutar desde la raíz:

```bash
bash AllmeshSTL
```

Verificado con OpenFOAM v2512. El script ejecuta `blockMesh`, `snappyHexMesh`, `topoSet` y `splitMeshRegions`; añade capas en el fluido y lo refina ×2 en dirección transversal x. Reemplaza las mallas anteriores sin archivarlas y guarda los logs en `logs/`.

Se generan inicialmente **3 capas** junto al sólido, con primera capa nominal de **2 µm** y crecimiento **1.25**. El refinamiento posterior subdivide también las capas normales a x.

| Región | Celdas finales |
|---|---:|
| Fluido | 33 600 |
| Sólido | 8 000 |
| **Total** | **41 600** |

Ambas regiones pasan `checkMesh`. El script exige menos de **50 000 celdas** en total.

## Archivos principales

- `system/blockMeshDict`: malla base.
- `system/snappyHexMeshDict` y `system/topoSetDict`: ajuste al STL y selección de regiones.
- `system/fluid/snappyHexMeshDict`: capas de inflación.
- `system/fluid/refineMeshDict`: refinamiento del fluido.
- `constant/fluid/polyMesh` y `constant/solid/polyMesh`: mallas finales.
- `old_geometry/`: diccionarios de la geometría anterior, sin mallas generadas.

## Ver en ParaView

Abrir `Microcanal.foam` desde la raíz y seleccionar las regiones `fluid` y `solid`. Desmarcar los campos en **Cell Arrays** y **Point Arrays**, desactivar **Decompose polyhedra** y pulsar **Apply**. Usar **Surface With Edges** para ver las celdas.

## Estado del caso

La geometría y la malla están listas para visualizar. La configuración de `chtMultiRegionFoam` está pendiente: los campos de `0/`, las propiedades físicas y las condiciones de contorno todavía corresponden al caso anterior. No se ha ejecutado una simulación con la nueva geometría.
