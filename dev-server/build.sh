#!/bin/bash

##sudo docker build -t registry.dev.proneer.co/dev-gpu-k8s:v0.1 -f Dockerfile.dev.k8s .
##sudo docker build -t registry.dev.proneer.co/dev-gpu-k8s:latest -f Dockerfile.dev.k8s .
sudo docker build -t registry.dev.proneer.co/dev-gpu:v0.1 -f Dockerfile.dev .
sudo docker build -t registry.dev.proneer.co/dev-gpu:latest -f Dockerfile.dev .

##sudo docker build -t registry.dev.proneer.co/dev-server-k8s:v0.1 -f Dockerfile.k8s.vscode .
##sudo docker build -t registry.dev.proneer.co/dev-server-k8s:latest -f Dockerfile.k8s.vscode .
sudo docker build -t registry.dev.proneer.co/dev-server:v0.1 -f Dockerfile.vscode .
sudo docker build -t registry.dev.proneer.co/dev-server:latest -f Dockerfile.vscode .

##sudo docker push registry.dev.proneer.co/dev-gpu:k8s:v0.1
##sudo docker push registry.dev.proneer.co/dev-gpu:k8s:latest
#sudo docker push registry.dev.proneer.co/dev-gpu:v0.1
#sudo docker push registry.dev.proneer.co/dev-gpu:latest

##sudo docker push registry.dev.proneer.co/dev-server-k8s:v0.1
##sudo docker push registry.dev.proneer.co/dev-server-k8s:latest
#sudo docker push registry.dev.proneer.co/dev-server:v0.1
#sudo docker push registry.dev.proneer.co/dev-server:latest
