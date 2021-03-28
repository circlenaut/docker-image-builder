#!/bin/bash

PS3='Choose which version to run: '
options=(
    "Ubuntu 18.04 with Cuda 10.1 and cuDNN7" \
    "Ubuntu 18.04 with Cuda 10.2 and cuDNN7" \
    "Ubuntu 20.04 with Cuda 11.0.3 and cuDNN8" \
    "Ubuntu 20.04 with Cuda 11.1.1 and cuDNN8" \
    "Ubuntu 20.04 with Cuda 11.2.1 and cuDNN8" \
    "Quit" \
)
COLUMNS=1000
select opt in "${options[@]}"; do
    case $opt in
        "Ubuntu 18.04 with Cuda 10.1 and cuDNN7")
            echo "Running image: $opt"
            if [ "$1" == "-i" ]; then
                sudo docker container run --name bionic_cuda_10-1_cudnn7 -it --rm --gpus all registry.dev.proneer.co/cuda:10.1-cudnn7-devel-ubuntu18.04
            else
                sudo docker container run --name bionic_cuda_10-1_cudnn7 --rm --gpus all registry.dev.proneer.co/cuda:10.1-cudnn7-devel-ubuntu18.04
            fi
            break
            ;;
        "Ubuntu 18.04 with Cuda 10.2 and cuDNN7")
            echo "Running image: $opt"
            if [ "$1" == "-i" ]; then
                sudo docker container run --name bionic_cuda_10-2_cudnn7 -it --rm --gpus all registry.dev.proneer.co/cuda:10.2-cudnn7-devel-ubuntu18.04
            else
                sudo docker container run --name bionic_cuda_10-2_cudnn7 --rm --gpus all registry.dev.proneer.co/cuda:10.2-cudnn7-devel-ubuntu18.04
            fi
            break
            ;;
        "Ubuntu 20.04 with Cuda 11.0.3 and cuDNN8")
            echo "Running image: $opt"
            if [ "$1" == "-i" ]; then
                sudo docker container run --name focal_cuda_11-0-3_cudnn8 -it --rm --gpus all registry.dev.proneer.co/cuda:11.0.3-cudnn8-devel-ubuntu20.04 /bin/bash
            else
                sudo docker container run --name focal_cuda_11-0-3_cudnn8 --rm --gpus all registry.dev.proneer.co/cuda:11.0.3-cudnn8-devel-ubuntu20.04
            fi
            break
            ;;
        "Ubuntu 20.04 with Cuda 11.1.1 and cuDNN8")
            echo "Running image: $opt"
            if [ "$1" == "-i" ]; then
                sudo docker container run --name focal_cuda_11-1-1_cudnn8 -it --rm --gpus all registry.dev.proneer.co/cuda:11.1.1-cudnn8-devel-ubuntu20.04
            else
                sudo docker container run --name focal_cuda_11-1-1_cudnn8 --rm --gpus all registry.dev.proneer.co/cuda:11.1.1-cudnn8-devel-ubuntu20.04
            fi
	        break
            ;;
        "Ubuntu 20.04 with Cuda 11.2.1 and cuDNN8")
            echo "Running image: $opt"
            if [ "$1" == "-i" ]; then
                sudo docker container run --name focal_cuda_11-2-1_cudnn8 -it --rm --gpus all registry.dev.proneer.co/cuda:11.2.1-cudnn8-devel-ubuntu20.04
            else
                sudo docker container run --name focal_cuda_11-2-1_cudnn8 --rm --gpus all registry.dev.proneer.co/cuda:11.2.1-cudnn8-devel-ubuntu20.04
            fi
	        break
            ;;
        "Quit")
            echo "User requested exit"
            exit
            ;;
        *) echo "invalid option $REPLY";;
    esac
done