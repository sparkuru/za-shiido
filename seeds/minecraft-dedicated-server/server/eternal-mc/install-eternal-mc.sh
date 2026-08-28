#/usr/bin/env zsh

installer_version="forge-1.12.2-14.23.5.2860-installer"
cd /home/game/minecraft/server/eternal-mc

java_bin_path="/home/app/java/zulu-jdk-v8.0.412-linux-x64/bin/java"
eval $java_bin_path \
    -Dhttp.proxyHost=192.168.9.4 \
    -Dhttp.proxyPort=7890 \
    -Dhttps.proxyHost=192.168.9.4 \
    -Dhttps.proxyPort=7890 \
    -jar $installer_version.jar \
    --installServer