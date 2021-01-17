sudo docker build -t registry.dev.proneer.co/core-gpu:base -f Dockerfile.base .
sudo docker build -t registry.dev.proneer.co/core-gpu:v0.1 -f Dockerfile.core .
sudo docker build -t registry.dev.proneer.co/core-gpu:latest -f Dockerfile.core .
sudo docker build -t registry.dev.proneer.co/core-gpu:dev -f Dockerfile.dev .
sudo docker build -t registry.dev.proneer.co/core-gpu:dev.conda -f Dockerfile.dev.conda .
sudo docker build -t registry.dev.proneer.co/core-gpu-k8s:v0.1 -f Dockerfile.dev.conda.k8s .
sudo docker build -t registry.dev.proneer.co/core-gpu-k8s:latest -f Dockerfile.dev.conda.k8s .
sudo docker build -t registry.dev.proneer.co/core-gpu-dev:v0.1 -f Dockerfile.dev.conda .
sudo docker build -t registry.dev.proneer.co/core-gpu-dev:latest -f Dockerfile.dev.conda .

#sudo docker push registry.dev.proneer.co/core-gpu:base
sudo docker push registry.dev.proneer.co/core-gpu:v0.1
sudo docker push registry.dev.proneer.co/core-gpu:latest
#sudo docker push registry.dev.proneer.co/core-gpu:dev
#sudo docker push registry.dev.proneer.co/core-gpu:dev.conda
sudo docker push registry.dev.proneer.co/core-gpu:k8s:v0.1
sudo docker push registry.dev.proneer.co/core-gpu:k8s:latest
sudo docker push registry.dev.proneer.co/core-gpu-dev:v0.1
sudo docker push registry.dev.proneer.co/core-gpu-dev:latest