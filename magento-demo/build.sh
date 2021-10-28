#!/bin/bash

sudo docker-compose down
sudo docker volume rm magento_cache_data
sudo docker volume rm magento_db_data
sudo docker volume rm magento_proxy_data
#sudo docker volume rm magento_dev_home
sudo docker volume rm magento_dev_workspace
sudo docker volume rm magento_dev_data
sudo docker volume rm magento_dev_apps
sudo docker volume list
sudo python ../Image-Builder/build.py --config build.yml --log_level debug --gzip --overwrite
sudo docker-compose up -d
sudo docker logs -f magento_dev
