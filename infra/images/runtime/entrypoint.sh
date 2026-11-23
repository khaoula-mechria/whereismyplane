#!/bin/sh
# SageMaker Training lance l'image avec l'argument « train » (convention BYOC) ;
# Lambda la lance avec le nom du handler (ImageConfig.Command).
# Les jobs Processing remplacent ce point d'entrée (ContainerEntrypoint).
set -e
if [ "$1" = "train" ]; then
  shift
  exec python3 -m aeropulse.mlops.train_job "$@"
fi
exec /lambda-entrypoint.sh "$@"
