FROM registry.dev.proneer.co/base-gpu:latest

######## STAGING ###########

USER root

### Technical Environment Variables
ENV \
    DEBIAN_FRONTEND=noninteractive \
    RESOURCES_PATH="/resources" \
    SCRIPTS_PATH="/scripts" \
    WORKSPACE_HOME="/workspace" \
    APPS_PATH="/apps" \
    DATA_PATH="/data"

### Create install and data directories
RUN \
    mkdir $RESOURCES_PATH && chmod a+rwx $RESOURCES_PATH \
    && mkdir $SCRIPTS_PATH && chmod a+rwx $SCRIPTS_PATH \
    && mkdir $APPS_PATH && chmod a+rwx $APPS_PATH \
    && mkdir $DATA_PATH && chmod a+rw $DATA_PATH

### Install runtime utilities
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        supervisor \
    # Cleanup
    && clean-layer.sh \
    # Fix permissions
    && fix-permissions.sh $HOME

### Install python packages
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3-systemd \
        python-crontab \
        python3-yaml \
        python3-typing-extensions \
        libyaml-dev \
    # Cleanup
    && clean-layer.sh \
    && rm -rf /var/lib/apt/lists/* \
    # Fix permissions
    && fix-permissions.sh $HOME

### Install Caddy
RUN echo "deb [trusted=yes] https://apt.fury.io/caddy/ /" | sudo tee -a /etc/apt/sources.list.d/caddy-fury.list
RUN apt-get update && apt-get install -y \
    libnss3-tools \
    caddy \
    # Fix permissions
    && fix-permissions.sh $HOME \
    # Cleanup
    && clean-layer.sh

### Place App dependencies here

### Create a new user
ARG UNAME=stager
ARG UID=1000
ARG GID=100
RUN groupadd --gid $GID -o $UNAME \
    && useradd \
      --uid $UID \
      --gid $GID \
      --create-home \
      --shell /bin/bash \ 
      $UNAME \
    && passwd -d $UNAME \
    && adduser $UNAME sudo
RUN echo "$UNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$UNAME \
    && chmod 0440 /etc/sudoers.d/$UNAME
WORKDIR /home/$UNAME

RUN cp -r /root/.bashrc /home/$UNAME \
    && chown -R $UNAME:$UNAME /home/$UNAME

### Copy some configuration files
COPY scripts/docker-entrypoint.py /
COPY scripts/run_staging.py $SCRIPTS_PATH
COPY scripts/__init__.py $SCRIPTS_PATH
COPY configs/supervisor/supervisord.conf /etc/supervisor/supervisord.conf
COPY configs/supervisor/conf.d /etc/supervisor/conf.d/
COPY configs/caddy/caddy.conf /etc/caddy/caddy.conf

### Fix permissions and cleanup
RUN \
    chmod -R a+rwx $RESOURCES_PATH \
    && chmod -R a+rwx $APPS_PATH \
    && chmod -R a+rw $DATA_PATH \
    && echo 'cd '$APPS_PATH >> /home/$UNAME/.bashrc \
    && chown -R $UNAME:$UNAME $RESOURCES_PATH \
    && chown -R $UNAME:$UNAME $APPS_PATH \
    && chown -R $UNAME:$UNAME $DATA_PATH \
    && chown -R $UNAME:$UNAME /home/$UNAME

EXPOSE 8300
#CMD ["code-server", "--host", "0.0.0.0", "--auth", "none", "--port", "8300"]

ENV WORKSPACE_PORT=8300

USER $UNAME

ENTRYPOINT ["python", "/docker-entrypoint.py"]
