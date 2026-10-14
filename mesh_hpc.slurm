#!/bin/bash
#SBATCH --job-name=mesh-microchannel3D141026
#SBATCH --partition=hpc
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

set -euo pipefail

module purge
module load openfoam/2506
source /opt/ohpc/pub/simulationPackages/openfoam/openfoam2506/OpenFOAM-v2506/etc/bashrc

cd "${SLURM_SUBMIT_DIR}"

echo "Nodo: $(hostname)"
echo "Trabajo: ${SLURM_JOB_ID}"
echo "Directorio: ${PWD}"

command -v surfaceCheck
command -v blockMesh
command -v snappyHexMesh
command -v splitMeshRegions
command -v refineMesh
command -v checkMesh

bash AllmeshSTL

echo "Malla generada y verificada correctamente."
