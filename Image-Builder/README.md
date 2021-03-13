# Setup

## Create Symlinks
"/opt/docker/Docker-Images" --> "/nfs/nfs1-gpu-cluster1-dal10-ibm/guests/<user>/Docker-Images/"
"/opt/docker/Docker-Images/Image-Builder/image-builder" --> "/usr/local/etc/image-builder"
"/opt/docker/Docker-Images/Image-Builder/schema.yaml" --> "/opt/docker/Docker-Images"

## Create Sudo Rule

Create or append to '/etc/sudoers.d/docker':
    
    %devs   ALL=(ALL)       NOPASSWD: /usr/bin/docker

make sure <user> is member of devs group