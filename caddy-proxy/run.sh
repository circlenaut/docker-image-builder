#!/bin/bash

sudo docker-compose down
sudo bash build.sh
sudo docker-compose up -d
sudo docker logs -f caddy-proxy
