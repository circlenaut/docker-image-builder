FROM registry.dev.proneer.co/gunicorn:latest
MAINTAINER proneer <phillip@proneer.co>

######## FastAPI ###########

### Image and project labels
LABEL \
    maintainer="proneer <phillip@proneer.co>" \
        org.label-schema.docker.dockerfile="/Dockerfile" \
        org.label-schema.name="FastAPI base image" \
        org.label-schema.url="https://www.proneer.co"

USER root

### Technical Environment Variables
ENV \
    USER_GID=0 \
    DEBIAN_FRONTEND=noninteractive

### Overwrite existing gunicorn config
COPY ./configs/supervisor/gunicorn.conf /etc/supervisor/conf.d/gunicorn.conf

### Install fastapi dependencies
USER gunicorn

COPY ./configs/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

COPY ./app /app
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]