#!/bin/bash

declare -a Containers=(
    "registry.dev.proneer.co/supervisor:nvidia-11.1-cudnn8-runtime-ubuntu20.04-py39"
)

for image in ${Containers[@]}; do
   echo "------------------------"
   echo "image: $image"
   sudo docker container run --rm --gpus all $image "ls -la /"
done