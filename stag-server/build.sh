#!/bin/bash

#sudo docker build -t registry.dev.proneer.co/stag-server:k8s -f Dockerfile.k8s .
sudo docker build -t registry.dev.proneer.co/stag-server-app:v0.1 -f Dockerfile.app .
sudo docker build -t registry.dev.proneer.co/stag-server-app:latest -f Dockerfile.app .

#sudo docker push registry.dev.proneer.co/stag-server:k8s
#sudo docker push registry.dev.proneer.co/stag-server-app:v0.1
#sudo docker push registry.dev.proneer.co/stag-server-app:latest
