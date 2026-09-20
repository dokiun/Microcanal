# Microcanal: caso de flujo multifase y cambio de fase

Este caso simula el flujo de un fluido en un microcanal con una zona de calentamiento y evaporación, usando un enfoque multiregión (`fluid` + `solid`) y un solver de cambio de fase en OpenFOAM.

## Descripción general

El modelo representa un canal rectangular de sección pequeña con paredes sólidas, donde se resuelve la dinámica del fluido y la transferencia de calor en el sólido. Se usa un esquema de dos fases (`water` y `air`) y una condición inicial con una zona sobrecalentada para desencadenar la evaporación.

La configuración está orientada a estudiar:

- flujo interno en microcanal,
- transferencia de calor entre sólido y fluido,
- evaporación directa y evolución del volumen de fase,
- comportamiento de la interfaz líquido-vapor en geometrías confinadas.

## Solver y entorno

- Solver principal: `multiRegionPhaseChangeFlow`
- Versión de OpenFOAM: `OpenFOAM/v2406-foss-2023a`
- Entorno de ejecución: BlueBEAR / SLURM
- Geometría: canal multiregión (`fluid` y `solid`)

## Geometría y malla

La malla se genera con `blockMesh` en dos regiones:

- Fluido: `constant/fluid/polyMesh`
- Sólido: `constant/solid/polyMesh`

La geometría del canal es aproximadamente:

- ancho de canal: 150 µm
- altura de canal: 300 µm
- grosor de pared: 50 µm
- longitud total: 6 mm

La malla se define en:

- `system/fluid/blockMeshDict`
- `system/solid/blockMeshDict`

Con una resolución de:

- `Nx = 33`
- `Ny = 75`
- `Nz = 400`

Se usa un refinamiento gradual en las direcciones `x` e `y` para mejorar la resolución cerca de las paredes y la zona de interés.

## Condiciones iniciales y frontera

Los campos iniciales se preparan en:

- `0/`
- `system/fluid/setFieldsDict`

Algunas condiciones relevantes:

- velocidad de entrada: flujo axial con velocidad inicial de aproximadamente 0.61 m/s,
- temperatura inicial: 372.15 K,
- fase inicial: `alpha.water = 1` en la mayor parte del dominio,
- región inicial sobrecalentada en una zona localizada para iniciar la evaporación,
- pared sólida con condiciones no-slip y acoplamiento térmico.

## Archivos clave

### Directorio raíz

- `runAllPrepareBlueBEAR.sh`: preparación del caso, generación de malla, campos iniciales y descomposición de dominio.
- `runCaseBlueBEAR.sh`: ejecución paralela del caso con SLURM.
- `runPostProcessBlueBEAR.sh`: postprocesado del caso.
- `AllrunCh`: script alternativo de ejecución.
- `Allclean`: limpieza del caso.

### Configuración física

- `constant/fluid/phaseChangeProperties`: modelo de cambio de fase.
- `constant/fluid/thermophysicalProperties`: propiedades termofísicas de las fases.
- `constant/regionProperties`: regiones del problema (`fluid`, `solid`).

### Control del caso

- `system/controlDict`: tiempos de simulación, intervalo de escritura, CFL, etc.
- `system/fvSchemes`: esquemas numéricos.
- `system/fvSolution`: solución lineal y controladores de iteración.

### Resultado y observación

- `0/`: condiciones iniciales y frontera.
- `0-orig-asp/`: copia original de condiciones iniciales.
- `system/cuttingPlanes`: funciones de postprocesado para cortes planos.
- `system/probes`: sondas para monitorización.

## Flujo de trabajo recomendado

### 1. Preparación del caso

Desde la raíz del caso:

```bash
bash runAllPrepareBlueBEAR.sh
```

Esto suele hacer lo siguiente:

- quitar el directorio `0` y restaurar la copia original,
- regenerar la malla de `fluid` y `solid`,
- aplicar `changeDictionary`,
- inicializar campos con `setFields`,
- renumerar malla,
- comprobar malla con `checkMesh`,
- descomponer el dominio para ejecución paralela.

### 2. Ejecución de la simulación

En un entorno con acceso a SLURM:

```bash
sbatch runCaseBlueBEAR.sh
```

El script usa:

```bash
mpirun multiRegionPhaseChangeFlow -parallel
```

con `#SBATCH --ntasks 40` y una duración de 48 horas.

### 3. Postprocesado

```bash
bash runPostProcessBlueBEAR.sh
```

Este paso está pensado para extraer resultados, visualizaciones o métricas del caso ya resuelto.

## Resultado esperado

La simulación genera directorios temporales del tipo:

- `0`, `0.0001`, `0.0002`, ...
- `postProcessing/`
- `log.*`

Los campos principales a revisar suelen ser:

- `alpha.water`: fracción de fase líquida,
- `p`, `p_rgh`: presión,
- `U`: velocidad,
- `T`, `T.air`, `T.water`: temperatura,
- `rho`, `mu`, etc. según el caso.

## Recomendaciones

- Antes de ejecutar la simulación completa, conviene revisar que la malla y el campo inicial sean consistentes.
- Si hay problemas de estabilidad, revisar:
  - `system/controlDict`
  - `system/fvSchemes`
  - `system/fvSolution`
  - `maxCo`, `maxAlphaCo` y `maxDeltaT`
- Para visualización, suele usarse paraFoam o herramientas de postprocesado de OpenFOAM.

## Observaciones

Este caso está pensado como un estudio de microfluídica con evaporación en un canal cerrado de pequeño tamaño, con acoplamiento térmico entre fluido y pared. La resolución espacial y temporal son importantes para capturar la evolución de la interfaz y el cambio de fase.

## Contacto / mantenimiento

Este README es una referencia rápida para el uso y comprensión del caso. Si se modifica la geometría, condiciones de contorno, flujo de trabajo o modelo físico, conviene actualizar este documento junto con los archivos de configuración.

# Microcanal: caso de flujo multifase y cambio de fase

Este caso simula el flujo de un fluido en un microcanal con una zona de calentamiento y evaporación, usando un enfoque multiregión (`fluid` + `solid`) y un solver de cambio de fase en OpenFOAM.

## Descripción general

El modelo representa un canal rectangular de sección pequeña con paredes sólidas, donde se resuelve la dinámica del fluido y la transferencia de calor en el sólido. Se usa un esquema de dos fases (`water` y `air`) y una condición inicial con una zona sobrecalentada para desencadenar la evaporación.

La configuración está orientada a estudiar:

- flujo interno en microcanal,
- transferencia de calor entre sólido y fluido,
- evaporación directa y evolución del volumen de fase,
- comportamiento de la interfaz líquido-vapor en geometrías confinadas.

## Solver y entorno

- Solver principal: `multiRegionPhaseChangeFlow`
- Versión de OpenFOAM: `OpenFOAM/v2406-foss-2023a`
- Entorno de ejecución: BlueBEAR / SLURM
- Geometría: canal multiregión (`fluid` y `solid`)

## Geometría y malla

La malla se genera con `blockMesh` en dos regiones:

- Fluido: `constant/fluid/polyMesh`
- Sólido: `constant/solid/polyMesh`

La geometría del canal es aproximadamente:

- ancho de canal: 150 µm
- altura de canal: 300 µm
- grosor de pared: 50 µm
- longitud total: 6 mm

La malla se define en:

- `system/fluid/blockMeshDict`
- `system/solid/blockMeshDict`

Con una resolución de:

- `Nx = 33`
- `Ny = 75`
- `Nz = 400`

Se usa un refinamiento gradual en las direcciones `x` e `y` para mejorar la resolución cerca de las paredes y la zona de interés.

## Condiciones iniciales y frontera

Los campos iniciales se preparan en:

- `0/`
- `system/fluid/setFieldsDict`

Algunas condiciones relevantes:

- velocidad de entrada: flujo axial con velocidad inicial de aproximadamente 0.61 m/s,
- temperatura inicial: 372.15 K,
- fase inicial: `alpha.water = 1` en la mayor parte del dominio,
- región inicial sobrecalentada en una zona localizada para iniciar la evaporación,
- pared sólida con condiciones no-slip y acoplamiento térmico.

## Archivos clave

### Directorio raíz

- `runAllPrepareBlueBEAR.sh`: preparación del caso, generación de malla, campos iniciales y descomposición de dominio.
- `runCaseBlueBEAR.sh`: ejecución paralela del caso con SLURM.
- `runPostProcessBlueBEAR.sh`: postprocesado del caso.
- `AllrunCh`: script alternativo de ejecución.
- `Allclean`: limpieza del caso.

### Configuración física

- `constant/fluid/phaseChangeProperties`: modelo de cambio de fase.
- `constant/fluid/thermophysicalProperties`: propiedades termofísicas de las fases.
- `constant/regionProperties`: regiones del problema (`fluid`, `solid`).

### Control del caso

- `system/controlDict`: tiempos de simulación, intervalo de escritura, CFL, etc.
- `system/fvSchemes`: esquemas numéricos.
- `system/fvSolution`: solución lineal y controladores de iteración.

### Resultado y observación

- `0/`: condiciones iniciales y frontera.
- `0-orig-asp/`: copia original de condiciones iniciales.
- `system/cuttingPlanes`: funciones de postprocesado para cortes planos.
- `system/probes`: sondas para monitorización.

## Flujo de trabajo recomendado

### 1. Preparación del caso

Desde la raíz del caso:

```bash
bash runAllPrepareBlueBEAR.sh
```

Esto suele hacer lo siguiente:

- quitar el directorio `0` y restaurar la copia original,
- regenerar la malla de `fluid` y `solid`,
- aplicar `changeDictionary`,
- inicializar campos con `setFields`,
- renumerar malla,
- comprobar malla con `checkMesh`,
- descomponer el dominio para ejecución paralela.

### 2. Ejecución de la simulación

En un entorno con acceso a SLURM:

```bash
sbatch runCaseBlueBEAR.sh
```

El script usa:

```bash
mpirun multiRegionPhaseChangeFlow -parallel
```

con `#SBATCH --ntasks 40` y una duración de 48 horas.

### 3. Postprocesado

```bash
bash runPostProcessBlueBEAR.sh
```

Este paso está pensado para extraer resultados, visualizaciones o métricas del caso ya resuelto.

## Resultado esperado

La simulación genera directorios temporales del tipo:

- `0`, `0.0001`, `0.0002`, ...
- `postProcessing/`
- `log.*`

Los campos principales a revisar suelen ser:

- `alpha.water`: fracción de fase líquida,
- `p`, `p_rgh`: presión,
- `U`: velocidad,
- `T`, `T.air`, `T.water`: temperatura,
- `rho`, `mu`, etc. según el caso.

## Recomendaciones

- Antes de ejecutar la simulación completa, conviene revisar que la malla y el campo inicial sean consistentes.
- Si hay problemas de estabilidad, revisar:
  - `system/controlDict`
  - `system/fvSchemes`
  - `system/fvSolution`
  - `maxCo`, `maxAlphaCo` y `maxDeltaT`
- Para visualización, suele usarse paraFoam o herramientas de postprocesado de OpenFOAM.

## Observaciones

Este caso está pensado como un estudio de microfluídica con evaporación en un canal cerrado de pequeño tamaño, con acoplamiento térmico entre fluido y pared. La resolución espacial y temporal son importantes para capturar la evolución de la interfaz y el cambio de fase.

## Contacto / mantenimiento

Este README es una referencia rápida para el uso y comprensión del caso. Si se modifica la geometría, condiciones de contorno, flujo de trabajo o modelo físico, conviene actualizar este documento junto con los archivos de configuración.

