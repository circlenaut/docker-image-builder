#!/bin/bash

sudo docker build -t registry.dev.proneer.co/base-gpu:v0.1 -f Dockerfile.base .
sudo docker build -t registry.dev.proneer.co/base-gpu:latest -f Dockerfile.base .

#sudo docker push registry.dev.proneer.co/base-gpu:v0.1
#sudo docker push registry.dev.proneer.co/base-gpu:latest
