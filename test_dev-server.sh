#!/bin/bash
sudo docker-compose down
cd core-gpu
sudo bash build.sh
cd ../dev-server/
sudo bash build.sh 
cd ..
sudo docker-compose up -d
sudo docker logs -f pod2-colab
