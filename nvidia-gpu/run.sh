#!/bin/bash

declare -a Containers=(
    "registry.dev.proneer.co/cuda:nvidia-11.1-cudnn8-runtime-ubuntu20.04"
    "registry.dev.proneer.co/cuda:slim-nvidia-11.1-cudnn8-runtime-ubuntu20.04"
)

for image in ${Containers[@]}; do
   echo "------------------------"
   echo "image: $image"
   sudo docker container run --rm --gpus all $image
done
