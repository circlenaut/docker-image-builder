FROM registry.dev.proneer.co/gunicorn:latest
MAINTAINER proneer <phillip@proneer.co>

######## Gunicorn Unicorn ###########

### Image and project labels
LABEL \
    maintainer="proneer <phillip@proneer.co>" \
        org.label-schema.docker.dockerfile="/Dockerfile.gunicorn" \
        org.label-schema.name="Uvicorn-Gunicorn base image" \
        org.label-schema.url="https://www.proneer.co"

USER root

### Technical Environment Variables
ENV \
    USER_GID=0 \
    DEBIAN_FRONTEND=noninteractive

COPY ./configs/conf.d /etc/supervisor/conf.d/
COPY ./configs/gunicorn_conf.py /gunicorn_conf.py

COPY ./scripts/start.sh /start.sh
RUN chmod +x /start.sh

COPY ./scripts/start-reload.sh /start-reload.sh
RUN chmod +x /start-reload.sh

COPY ./configs/requirements.txt /tmp/requirements.txt
COPY ./app /app

### Add gunicorn user and fix permissions
RUN \ 
    useradd -ms /bin/bash gunicorn \
    && chown -R gunicorn:gunicorn \
        /gunicorn_conf.py \
        /start.sh \
        /start-reload.sh \
        /app

ENV PYTHONPATH=/app

EXPOSE 8000

USER gunicorn

ENV PATH="/home/gunicorn/.local/bin:${PATH}"
RUN python -m pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /app/

CMD ["/start.sh"]