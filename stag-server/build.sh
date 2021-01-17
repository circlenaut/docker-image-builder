sudo docker build -t proneer/stag-server:k8s -f Dockerfile.k8s .
sudo docker build -t proneer/stag-server-app:latest -f Dockerfile.k8s.app .


#docker push proneer/stag-server:k8s
#docker push proneer/stag-server-app:latest
