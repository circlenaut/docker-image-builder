#!/bin/bash

sudo docker-compose down
cd ../caddy-proxy
sudo bash build.sh
cd ../base-gpu
sudo bash build.sh
cd ../stag-server/
sudo bash build.sh
sudo docker-compose up -d
sudo docker logs -f stag-test
