from .core import Docker


def main():
    docker = Docker()
    docker.build()

if __name__ == '__main__':
    main()