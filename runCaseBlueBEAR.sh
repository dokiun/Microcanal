#!/bin/bash -l
# -------------------------
#SBATCH --ntasks 40
#SBATCH --mem-per-cpu 1G
#SBATCH --time  48:00:00 
#SBATCH --mail-type All
#SBATCH --job-name=channel3DV16-220526
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --account=alberinf-operating-theatre-fluid-flow
#SBATCH --qos bbdefault # castles # bbshort # 
# -------------------------
#set -e

module purge; module load bluebear
module load bear-apps/2023a/live
module load OpenFOAM/v2406-foss-2023a
source $FOAM_BASH
source $WM_PROJECT_DIR/bin/tools/RunFunctions

mpirun multiRegionPhaseChangeFlow  -parallel 

