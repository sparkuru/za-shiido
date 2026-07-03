#!/usr/bin/env sh
# Forge requires a configured set of both JVM and program arguments.
# Add custom JVM arguments to the user_jvm_args.txt
# Add custom program arguments {such as nogui} to this file in the next line before the "$@" or
#  pass them to this script directly

version="1.20.1-47.4.1"
java_version="zulu-jdk-v17.0.11-linux-x64"

export JAVA_HOME="/home/wkyuu/cargo/lang/java/$java_version"
export PATH="$JAVA_HOME/bin:$PATH"

cd /home/wkyuu/cargo/game/minecraft/server/touhou-tinker-fantasy
java @user_jvm_args.txt @libraries/net/minecraftforge/forge/$version/unix_args.txt "$@" nogui