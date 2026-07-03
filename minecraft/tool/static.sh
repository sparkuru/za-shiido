#!/usr/bin/zsh

script_dir=${0:A:h}
minecraft_path=${MINECRAFT_PATH:-${script_dir:h}}
statics_path="$minecraft_path/tool/static"
package_name=$1

if [[ $1 == "" ]]; then
    echo "Usage: ./static.sh package_name"
    exit
fi

if [[ ! "$package_name" =~ '^[A-Za-z0-9._-]+$' ]]; then
    echo "Invalid package name: $package_name"
    exit 1
fi

target_path=${MINECRAFT_SERVER_DIR:-$minecraft_path/server}/$package_name

if [[ ! -d "$target_path" ]]; then
    echo "Target server directory does not exist: $target_path"
    exit 1
fi

for file in "$statics_path"/*; do
    target="$target_path/${file:t}"
    if [[ -e "$target" && ! -L "$target" ]]; then
        echo "Skip existing non-symlink: $target"
        continue
    fi
    ln -sfn "$file" "$target"
done
