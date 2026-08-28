#/usr/bin/env sh
# Forge requires a configured set of both JVM and program arguments.
# Add custom JVM arguments to the user_jvm_args.txt
# Add custom program arguments {such as nogui} to this file in the next line before the "$@" or
#  pass them to this script directly

cd /home/game/minecraft/server/eternal-mc

java_bin_path="/home/app/java/zulu-jdk-v8.0.412-linux-x64/bin/java"
eval $java_bin_path \
    -Xms128M \
    -Xmx10G \
    -server \
    -XX:+UseG1GC \
    -XX:-UseAdaptiveSizePolicy \
    -XX:-OmitStackTraceInFastThrow \
    -Dfml.ignoreInvalidMinecraftCertificates=True \
    -Dfml.ignorePatchDiscrepancies=True \
    -Dfile.encoding=utf-8 \
    -javaagent:/home/game/minecraft/tool/authlib-injector.jar=https://littleskin.cn/api/yggdrasil \
    -Dhttp.proxyHost=192.168.9.4 \
    -Dhttp.proxyPort=7890 \
    -Dhttps.proxyHost=192.168.9.4 \
    -Dhttps.proxyPort=7890 \
    -jar forge-1.12.2-14.23.5.2860.jar \
    nogui
