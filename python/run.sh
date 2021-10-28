#!/bin/bash

declare -a Containers=(
    "registry.dev.proneer.co/python:slim-nvidia-11.1-cudnn8-runtime-ubuntu20.04-py39"
    "registry.dev.proneer.co/python:nvidia-11.1-cudnn8-runtime-ubuntu20.04-py39"
)

for image in ${Containers[@]}; do
   echo "------------------------"
   echo "image: $image"
   sudo docker container run --rm --gpus all $image
done
