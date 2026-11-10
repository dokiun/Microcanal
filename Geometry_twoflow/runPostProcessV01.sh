#!/bin/bash -l
# -----------------------------------------------------------------------------
# Reconstrucción de resultados del caso NUEVO
# -----------------------------------------------------------------------------

#SBATCH --ntasks 1
#SBATCH --mem 4G
#SBATCH --time 1:00:00
#SBATCH --mail-type ALL
#SBATCH --job-name=post-thisCase-nuevo
#SBATCH --output=P-%x.%j.out
#SBATCH --error=P-%x.%j.err
#SBATCH --partition=hpc-short

set -e

module load openfoam/2412
source "$FOAM_BASH"
source "$WM_PROJECT_DIR/bin/tools/RunFunctions"

runApplication -s 1 reconstructPar -allRegions -newTimes
mv log.reconstructPar.1 "reconstructPar-$(date +"%Y_%m_%d_%I_%M_%p")-V01.log"

echo "Reconstrucción del caso NUEVO completada."
exit 0
