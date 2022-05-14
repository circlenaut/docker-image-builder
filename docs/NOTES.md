"""
Build script adapted from docker-py

Refs:
- https://docker-py.readthedocs.io/en/stable/images.html
- https://github.com/docker/docker-py/blob/master/docker/utils/build.py
- https://github.com/docker/docker-py/blob/master/docker/api/build.py
- https://github.com/docker/docker-py/blob/master/docker/utils/decorators.py
- https://github.com/docker/docker-py/blob/master/docker/utils/fnmatch.py
- https://docs.docker.com/engine/context/working-with-contexts/
- https://github.com/docker/docker-py/issues/538
- https://github.com/docker/docker-py/pull/209
- https://github.com/docker/docker-py/issues/974
- https://github.com/docker/docker-py/issues/2079
- https://github.com/docker/docker-py/issues/980
- https://github.com/docker/docker-py/issues/2682
- https://stackoverflow.com/questions/58204987/docker-python-client-not-building-image-from-custom-context
- https://stackoverflow.com/questions/53743886/create-docker-from-tar-with-python-docker-api

"""

#@TODO:
- Check if run as root
# - incorporate elements from these:
#   https://raw.githubusercontent.com/bgruening/docker-build/master/build.py
#   https://github.com/AlienVault-Engineering/pybuilder-docker/blob/master/src/main/python/pybuilder_docker/__init__.py
#   https://github.com/stencila/dockta