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

## Definición automática de las regiones sólido-fluido

La geometría STL se utiliza para definir directamente la región sólida del dominio. En "snappyHexMeshDict", las celdas ubicadas dentro de la superficie cerrada del STL se asignan a la "cellZone" denominada "solid".

Posteriormente, "topoSet" genera la región "fluid" como el complemento de la región sólida, es decir:

fluid = todas las celdas del dominio - solid

Finalmente, "splitMeshRegions -cellZonesOnly" utiliza las "cellZones" "solid" y "fluid" para generar las mallas independientes:
```
constant/
├── fluid/
│   └── polyMesh/
└── solid/
    └── polyMesh/
```
Esta estrategia permite cambiar fácilmente la geometría sólida sin redefinir manualmente la región fluida. Por ejemplo, el STL puede representar un perfil en T, una sección rectangular, un perfil rectangular hueco u otra geometría cerrada. En todos los casos, el material contenido por el STL se considera sólido y el volumen restante dentro del dominio de "blockMesh" se asigna al fluido.

```

STL
 │
 ▼
snappyHexMesh
 │
 └── cellZone: solid
          │
          ▼
       topoSet
          │
          └── fluid = dominio - solid
                    │
                    ▼
              cellZone: fluid
                    │
                    ▼
        splitMeshRegions
             /          \
          fluid         solid
```

Para que este procedimiento funcione correctamente, la geometría STL debe representar una superficie cerrada y válida, y "locationInMesh" debe encontrarse en una posición coherente con el dominio que se desea conservar.

## Estado del caso

La geometría y la malla están listas para visualizar. La configuración de `chtMultiRegionFoam` está pendiente: los campos de `0/`, las propiedades físicas y las condiciones de contorno todavía corresponden al caso anterior. No se ha ejecutado una simulación con la nueva geometría.
