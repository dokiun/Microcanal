#!/bin/bash -l
# -----------------------------------------------------------------------------
# Preparación del caso NUEVO
# 1) Genera la malla desde el STL del microcanal.
# 2) Verifica la malla.
# 3) Descompone la malla para correr en paralelo.
# -----------------------------------------------------------------------------

#SBATCH --ntasks 1
#SBATCH --mem 8G
#SBATCH --time 1:00:00
#SBATCH --mail-type ALL
#SBATCH --job-name=pre-processing-nuevo
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --partition=hpc-short

set -e

module load openfoam/2412
source "$FOAM_BASH"
source "$WM_PROJECT_DIR/bin/tools/RunFunctions"

# Generar la malla desde el STL importado y validarla.
./AllmeshSTL

# Verificar malla total y por región.
runApplication -s 1 checkMesh -allRegions -allTopology
mv log.checkMesh.1 "checkMesh-$(date +"%Y_%m_%d_%I_%M_%p").log"

# Descomponer para el cálculo paralelo.
runApplication decomposePar -allRegions -latestTime
mv log.decomposePar "decomposePar-$(date +"%Y_%m_%d_%I_%M_%p").log"

echo "Preparación del caso NUEVO completada."
exit 0
