#!/usr/bin/env sh
# Forge requires a configured set of both JVM and program arguments.
# Add custom JVM arguments to the user_jvm_args.txt
# Add custom program arguments {such as nogui} to this file in the next line before the "$@" or
#  pass them to this script directly

version="1.20.1-47.2.6"

cd /home/games/minecraft/servers/terra-firma-rebirth
java @user_jvm_args.txt @libraries/net/minecraftforge/forge/$version/unix_args.txt "$@" nogui