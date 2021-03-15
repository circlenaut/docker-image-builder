#!/bin/bash

echo "Loading magento2 site"
sudo a2ensite magento2

sudo supervisorctl stop apache2
sudo service apache2 stop
sudo supervisorctl start apache2
