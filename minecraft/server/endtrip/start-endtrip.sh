#!/usr/bin/env sh
# Forge requires a configured set of both JVM and program arguments.
# Add custom JVM arguments to the user_jvm_args.txt
# Add custom program arguments {such as nogui} to this file in the next line before the "$@" or
#  pass them to this script directly

cd /home/wkyuu/cargo/game/minecraft/server/endtrip
java_binary=/home/wkyuu/cargo/lang/java/zulu-jdk-v11.0.23-linux-x64/bin/java
$java_binary @user_jvm_args.txt -jar server.jar nogui