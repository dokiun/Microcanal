#!/bin/bash -l
# -----------------------------------------------------------------------------
# Ejecución del caso NUEVO
# -----------------------------------------------------------------------------

#SBATCH --ntasks 40
#SBATCH --mem-per-cpu 1G
#SBATCH --time 72:00:00
#SBATCH --mail-type All
#SBATCH --job-name=nuevo-case
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --partition=hpc-long

set -e

module load openfoam/2412
source "$FOAM_BASH"
source "$WM_PROJECT_DIR/bin/tools/RunFunctions"

mpirun multiRegionPhaseChangeFlow -parallel

exit 0
