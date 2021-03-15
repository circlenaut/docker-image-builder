#!/bin/bash

a2enmod rewrite
mkdir ~/.temp
curl -o ~/.temp/composer-setup.php https://getcomposer.org/installer
curl -o ~/.temp/composer-setup.sig https://composer.github.io/installer.sig
echo test1
php7.2 -r "if (hash('SHA384', file_get_contents('$HOME/.temp/composer-setup.php')) !== trim(file_get_contents('$HOME/.temp/composer-setup.sig'))) { unlink('$HOME/.temp/composer-setup.php'); echo 'Invalid installer' . PHP_EOL; exit(1); }"
echo test2
php7.2 ~/.temp/composer-setup.php --no-ansi --install-dir= ~/.local/bin --filename=composer
rm ~/.temp/composer-setup.php
chmod +x  ~/.local/bin/composer
curl -o n98-magerun2.phar http://files.magerun.net/n98-magerun2-latest.phar
chmod +x ./n98-magerun2.phar
chmod +x /workspace/installers/magento.sh
chmod +r /credis.php
mv n98-magerun2.phar ~/.local/bin
mkdir -p ~/.composer

a2enmod rewrite
mkdir ~/.temp
curl -o ~/.temp/composer-setup.php https://getcomposer.org/installer
curl -o ~/.temp/composer-setup.sig https://composer.github.io/installer.sig
echo test1
php7.2 -r "if (hash('SHA384', file_get_contents('$HOME/.temp/composer-setup.php')) !== trim(file_get_contents('$HOME/.temp/composer-setup.sig'))) { unlink('$HOME/.temp/composer-setup.php'); echo 'Invalid installer' . PHP_EOL; exit(1); }"
echo test2
php7.2 ~/.temp/composer-setup.php --no-ansi --install-dir= ~/.local/bin --filename=composer
rm ~/.temp/composer-setup.php
chmod +x  ~/.local/bin/composer
curl -o n98-magerun2.phar http://files.magerun.net/n98-magerun2-latest.phar
chmod +x ./n98-magerun2.phar
chmod +x /workspace/installers/magento.sh
chmod +r /credis.php
mv n98-magerun2.phar ~/.local/bin