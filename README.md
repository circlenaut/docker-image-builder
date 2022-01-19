# Setup

## Create Symlinks
"/nfs/nfs1-gpu-cluster1-dal10-ibm/guests/{user}/Docker-Images/" --> "/opt/docker/Docker-Images"
"/opt/docker/Docker-Images/Image-Builder/image-builder" --> "/usr/local/bin/image-builder"
"/opt/docker/Docker-Images/Image-Builder/schema.yaml" --> "/usr/local/etc/image-builder/schema.yaml"

## Create Sudo Rule

This script requires elevated permission, run with sudo.

Create or append to: '/etc/sudoers.d/docker'
    
    %devs   ALL=(ALL)       NOPASSWD: /usr/bin/docker

make sure "user" is member of the "devs" group