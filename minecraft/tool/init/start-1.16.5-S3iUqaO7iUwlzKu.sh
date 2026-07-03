#!/usr/bin/env sh
# Forge requires a configured set of both JVM and program arguments.
# Add custom JVM arguments to the user_jvm_args.txt
# Add custom program arguments {such as nogui} to this file in the next line before the "$@" or
#  pass them to this script directly

java_version="zulu-jdk-v17.0.11-linux-x64"

export JAVA_HOME="/home/wkyuu/cargo/lang/java/$java_version"
export PATH="$JAVA_HOME/bin:$PATH"

cd __SERVER_DIR__/S3iUqaO7iUwlzKu
java @user_jvm_args.txt -jar server.jar nogui
