#!/bin/bash
#SBATCH --job-name=microchannel3D141026
#SBATCH --partition=hpc
#SBATCH --time=48:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

set -euo pipefail

module purge
module load openmpiV2/5.0.7
module load openfoam/2506
source /opt/ohpc/pub/simulationPackages/openfoam/openfoam2506/OpenFOAM-v2506/etc/bashrc

cd "${SLURM_SUBMIT_DIR}"

command -v chtMultiRegionTwoPhaseEulerFoam
command -v checkMesh
command -v decomposePar

echo "Nodo: $(hostname)"
echo "Trabajo: ${SLURM_JOB_ID}"
echo "Directorio: ${PWD}"
echo "Tareas: ${SLURM_NTASKS}"

checkMesh -constant -region fluid
checkMesh -constant -region solid

decomposePar -allRegions -force

srun chtMultiRegionTwoPhaseEulerFoam -parallel
