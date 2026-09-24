# Geometría y mallado desde STL

`Microcanal.stl` es la fuente original, en milímetros. Representa el sólido
con sección en I, extruido desde z = 0 hasta z = 10 mm. El STL está cerrado
y contiene 44 triángulos. No se modifica al generar la malla.

El dominio exterior es un rectángulo de 0.30 × 0.40 mm:

- x: -0.15 a 0.15 mm; y: -0.20 a 0.20 mm.
- Alma sólida: x entre -0.075 y 0.075 mm.
- Alas superior e inferior: 0.05 mm de espesor.
- Dos medios canales laterales: 0.075 × 0.30 mm, longitud 10 mm.
- Referencia MC-RC: planos de simetría en x = ±0.15 mm (`outerLeft`, `outerRight`), tanto en sólido como en fluido. El canal completo mide 0.15 × 0.30 mm y su Dh es 200 µm.
- `blockMeshDict` genera esos patches como `symmetryPlane`; el mallado y la separación de regiones conservan su tipo.
- Volumen sólido esperado: 0.75 mm³; fluido total: 0.45 mm³.

## Generación

Con el entorno OpenFOAM cargado, ejecutar desde la raíz:

```bash
bash AllmeshSTL
```

1. Convierte una copia del STL a metros en `constant/triSurface`.
2. Extrae las aristas con `surfaceFeatureExtract`.
3. Genera la envolvente rectangular con `system/blockMeshDict`.
4. Refina y ajusta la interfaz con `system/snappyHexMeshDict`.
5. Define el fluido como el complemento de la zona sólida con `topoSet`.
   Reemplaza las mallas regionales anteriores sin archivar los resultados.
6. Separa las zonas mediante `splitMeshRegions -cellZonesOnly -overwrite`.
7. Añade tres capas en `fluid_to_solid` mediante `snappyHexMesh -region fluid`.
8. Refina todas las celdas fluidas en x con `refineMesh` (factor 2).
9. Comprueba ambas mallas y el límite total de celdas mediante `checkMesh`.

Los dos canales, aunque desconectados entre sí, pertenecen a una única
región `fluid`. La región `solid` contiene la pieza en I. La malla conjunta
previa a las capas se conserva en `constant/polyMesh`; las finales están en
`constant/fluid/polyMesh` y `constant/solid/polyMesh`.

La malla base tiene 8 × 8 × 200 = **12 800 celdas** (37.5 × 50 × 50 µm).
`snappyHexMesh` usa nivel de refinamiento 0 y ajusta la interfaz al STL.
Tras separar las regiones, añade **3 capas solo en el lado fluido de la
interfaz con el sólido**, con primera capa nominal de 2 µm, factor de
crecimiento 1.25 y espesor total de 7.625 µm. La cobertura obtenida es
del 100 % de las 4 000 caras de interfaz. La configuración está en
`system/fluid/snappyHexMeshDict` y el informe en `logs/log.snappyHexMesh.layers`.
Después de generar las capas, `refineMesh` divide las celdas fluidas en
la dirección transversal x, conservando las capas y el volumen. Las capas
normales a x también se subdividen (espesor nominal mínimo de 1 µm).
La configuración está en `system/fluid/refineMeshDict`.
Resultado: **8 000 celdas sólidas y 33 600 fluidas**, total **41 600**,
con dos canales desconectados. Se eligió factor 2 en vez de 8 para respetar
el límite acordado. El script exige menos de
50 000 celdas en total. Es una malla para inspeccionar la geometría,
sin estudio de independencia de malla.

## Visualización en ParaView

Abrir `Microcanal.foam` de la raíz, seleccionar las regiones `fluid` y
`solid` en **Mesh Regions** y pulsar **Apply**. Usar **Surface With Edges**
para mostrar la malla; ocultar `solid` para ver los dos canales.
Desactivar **Decompose polyhedra** en las propiedades avanzadas del lector
para visualizar y contar las 41 600 celdas originales; activado, ParaView
subdivide algunos poliedros para visualización y muestra 60 800 elementos.
Para inspeccionar solo la geometría, desmarcar los campos en **Cell Arrays**
y **Point Arrays**, ya que los campos de `0/` aún corresponden al caso anterior.

## Alcance

Este procedimiento prepara geometría y mallas. Los campos en `0/`, parte de las
condiciones físicas y los scripts antiguos de preparación corresponden
al caso anterior. Las condiciones laterales de todos los campos ya usan
`symmetryPlane`; el caso físico se migró a `chtMultiRegionTwoPhaseEulerFoam`, transitorio con cambio de fase, según el README principal.
Usar `AllmeshSTL` para este mallado, no `AllrunCh` ni los scripts antiguos
`runAllPrepare*`, que dependen de los diccionarios archivados.
 