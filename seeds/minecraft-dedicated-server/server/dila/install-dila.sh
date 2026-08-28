#!/usr/bin/zsh

installer_version="forge-1.20.1-47.4.0-installer"
cd /home/wkyuu/cargo/game/minecraft/server/dila

java \
    -Dhttp.proxyHost=192.168.9.2 \
    -Dhttp.proxyPort=1080 \
    -Dhttps.proxyHost=192.168.9.2 \
    -Dhttps.proxyPort=1080 \
    -jar $installer_version.jar \
    --installServer