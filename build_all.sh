#!/bin/bash

# Process Cuda images
sudo image-builder --overwrite --log_level debug ./base-gpu/build-bionic-cuda101-cudnn7.yml
sudo image-builder --overwrite --log_level debug ./base-gpu/build-bionic-cuda102-cudnn7.yml
sudo image-builder --overwrite --log_level debug ./base-gpu/build-focal-cuda1103-cudnn8.yml
sudo image-builder --overwrite --log_level debug ./base-gpu/build-focal-cuda1111-cudnn8.yml
sudo image-builder --overwrite --log_level debug ./base-gpu/build-focal-cuda1121-cudnn8.yml

# Process generic images
sudo image-builder --overwrite --log_level debug ./dev-server/build-focal-cuda110-cudnn8.yml
sudo image-builder --overwrite --log_level debug ./dev-server/build-nvidia-focal-cuda111-cudnn8.yml

# Process Flashlight
sudo image-builder --overwrite --log_level debug ./flashlight/build-focal-cpu.yml --pull
sudo image-builder --overwrite --log_level debug ./flashlight/build-focal-cuda.yml --pull

# Process Magento
sudo image-builder --overwrite --log_level debug ./magento-demo/build.yml --pull

# Process Openpose
sudo image-builder --overwrite --log_level debug ./openpose/build-bionic.yml --pull
sudo image-builder --overwrite --log_level debug ./openpose/build-bionic-dev.yml --pull
sudo image-builder --overwrite --log_level debug ./openpose/build-focal.yml --pull
sudo image-builder --overwrite --log_level debug ./openpose/build-focal-dev.yml --pull
