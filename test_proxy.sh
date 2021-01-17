#!/bin/bash
sudo docker-compose down
cd caddy-proxy
sudo bash build.sh
cd ..
sudo docker-compose up -d
sudo docker logs -f caddy-proxy
