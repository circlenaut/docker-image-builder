#!/bin/bash

a2enmod rewrite

#curl -o n98-magerun2.phar http://files.magerun.net/n98-magerun2-latest.phar
#chmod +x ./n98-magerun2.phar
#chmod +x /workspace/installers/magento.sh
#sudo chmod +r /credis.php
#sudo mv n98-magerun2.phar $HOME/.local/bin
#mkdir -p $HOME/.composer
#mkdir -p /workspace/.composer # if doesn't exist


curl -sS https://getcomposer.org/installer | sudo php -- --install-dir=/usr/local/bin --filename=composer --version=1.10.17

WORKSPACE="/workspace"
MAGENTO_VERSION="2.4.1"
MAGENTO_SECURITY_VERSION="1.1.0"
MAGENTO_ROOT="$WORKSPACE/magento2"
MAGENTO_DB_HOST="db"
MAGENTO_DB_NAME="magento2"
MAGENTO_DB_USER="magento2"
MAGENTO_DB_PASSWORD="magento2"
MAGENTO_DOMAIN="pod2.colab.proneer.co"
MAGENTO_ADMIN_USER="admin"
MAGENTO_ADMIN_PASSWORD="adminpass1234"
MAGENTO_ADMIN_EMAIL="admin@proneer.co"
MAGENTO_ADMIN_FIRSTNAME="admin"
MAGENTO_ADMIN_LASTNAME="user"
MAGENTO_ELASTIC_HOST="elasticsearch"
MAGENTO_ELASTIC_PORT="9200"
MAGENTO_ELASTIC_INDEX_PREFIX="magento_dev"
MAGENTO_REDIS_HOST="cache"
MAGENTO_REDIS_PORT="6379"
MAGENTO_REDIS_DB="0"
MAGENTO_REDIS_PASSWORD="redis"

mkdir $MAGENTO_ROOT
#mkdir $MAGENTO_ROOT/www && git clone https://github.com/magento/magento2 $MAGENTO_ROOT/www && cd $MAGENTO_ROOT/www
#git checkout -b proneer-$MAGENTO_VERSION $MAGENTO_VERSION
#mkdir $MAGENTO_ROOT/sample-data && git clone https://github.com/magento/magento2-sample-data $MAGENTO_ROOT/sample-data && cd $MAGENTO_ROOT/sample-data
#git checkout -b proneer-$MAGENTO_VERSION $MAGENTO_VERSION
#mkdir $MAGENTO_ROOT/security-package && git clone https://github.com/magento/security-package $MAGENTO_ROOT/security-package && cd $MAGENTO_ROOT/security-package
#git checkout -b proneer-$MAGENTO_SECURITY_VERSION $MAGENTO_SECURITY_VERSION

mkdir $MAGENTO_ROOT/www && curl -fsSL https://github.com/magento/magento2/archive/$MAGENTO_VERSION.tar.gz | tar -xzC $MAGENTO_ROOT/www --strip-components=1
mkdir $MAGENTO_ROOT/sample-data && curl -fsSL https://github.com/magento/magento2-sample-data/archive/$MAGENTO_VERSION.tar.gz | tar -xzC $MAGENTO_ROOT/sample-data --strip-components=1
mkdir $MAGENTO_ROOT/security-package && curl -fsSL https://github.com/magento/security-package/archive/$MAGENTO_SECURITY_VERSION.tar.gz | tar -xzC $MAGENTO_ROOT/security-package --strip-components=1

php -f $MAGENTO_ROOT/sample-data/dev/tools/build-sample-data.php -- --ce-source="$MAGENTO_ROOT/www"

cd $MAGENTO_ROOT/www
find var generated vendor pub/static pub/media app/etc -type f -exec chmod g+w {} +
find var generated vendor pub/static pub/media app/etc -type d -exec chmod g+ws {} +
sudo chown -R :www-data .
sudo chmod u+x bin/magento

echo "export PATH=$PATH:$MAGENTO_ROOT/www/bin" | tee -a $HOME/.bashrc
echo "export PATH=$PATH:$MAGENTO_ROOT/www/bin" | tee -a $HOME/.zshrc

composer install

cp $WORKSPACE/.magento2/auth.json $MAGENTO_ROOT/www && sudo chmod 400 $WORKSPACE/.magento2/auth.json

bin/magento setup:install \
	--db-host=$MAGENTO_DB_HOST \
	--db-name=$MAGENTO_DB_NAME \
	--db-user=$MAGENTO_DB_USER \
	--db-password=$MAGENTO_DB_PASSWORD \
	--cleanup-database \
	--skip-db-validation \
	--base-url=http://$MAGENTO_DOMAIN/ \
	--base-url-secure=https://$MAGENTO_DOMAIN/ \
	--use-secure=1 \
	--use-secure-admin=1 \
	--use-rewrites=1 \
	--backend-frontname=admin \
	--admin-user=$MAGENTO_ADMIN_USER \
	--admin-password=$MAGENTO_ADMIN_PASSWORD \
	--admin-email=$MAGENTO_ADMIN_EMAIL \
	--admin-firstname=$MAGENTO_ADMIN_FIRSTNAME \
	--admin-lastname=$MAGENTO_ADMIN_LASTNAME \
	--language=en_US \
	--currency=USD \
	--timezone=UTC \
	--elasticsearch-host=$MAGENTO_ELASTIC_HOST \
	--elasticsearch-port=$MAGENTO_ELASTIC_PORT \
	--elasticsearch-index-prefix=$MAGENTO_ELASTIC_INDEX_PREFIX \
	--search-engine=elasticsearch7 \
	--session-save=redis \
	--session-save-redis-host=$MAGENTO_REDIS_HOST \
	--session-save-redis-port=$MAGENTO_REDIS_PORT \
	--session-save-redis-password=$MAGENTO_REDIS_PASSWORD \
	--session-save-redis-db=$MAGENTO_REDIS_DB \
	--session-save-redis-log-level=7 \
	&& sudo chown -R :www-data .

composer update
bin/magento setup:upgrade
bin/magento cron:install
# composer require msp/twofactorauth
# bin/magento config:set twofactorauth/general/force_providers google

sudo a2ensite magento2





