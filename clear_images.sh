#!/bin/bash

sudo docker stop $(docker ps -a -q)
sudo docker rm -f $(docker ps -a -q)
sudo docker volume rm $(docker volume ls -q)
sudo docker system prune --all
