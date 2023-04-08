#!/bin/bash
if [[ $1 = "prod" || $1 = "dev" ]] && [[ $2 = "down" || $2 = "up" ]]; then
    cd ..
    fileEnv="docker-compose.${1}.yml"
    downOrUp=$2
    extraArgs=${@:3}
    echo "Running sudo docker compose -f docker-compose.yml -f $fileEnv $downOrUp $extraArgs"
    sudo docker compose -f docker-compose.yml -f $fileEnv $downOrUp $extraArgs
else
    echo 'Need to follow format ./deploy prod|dev down|up'
fi