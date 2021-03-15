#!/bin/bash

sudo docker build -t registry.dev.proneer.co/caddy-proxy:base -f Dockerfile.base .
sudo docker build -t registry.dev.proneer.co/caddy-proxy:v0.2 -f Dockerfile.caddy .
sudo docker build -t registry.dev.proneer.co/caddy-proxy:latest -f Dockerfile.caddy .

sudo docker push registry.dev.proneer.co/caddy-proxy:v0.2
sudo docker push registry.dev.proneer.co/caddy-proxy:latest