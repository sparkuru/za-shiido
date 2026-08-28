#!/bin/bash

set -euo pipefail

root_dir="${MINECRAFT_SERVER_DIR:-/home/wkyuu/cargo/game/minecraft/server}"

if [[ $# -ne 3 ]]; then
    echo "Usage: ./change_uuid.sh package_name old_uuid new_uuid"
    exit 1
fi

package_dir=$1
old_uuid=$2
new_uuid=$3
work_dir="$root_dir/$package_dir/world"

if [[ ! "$package_dir" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "Invalid package name: $package_dir"
    exit 1
fi

if [[ ! -d "$work_dir" ]]; then
    echo "World directory does not exist: $work_dir"
    exit 1
fi

find "$work_dir" \
    -depth \
    -name "*$old_uuid*" \
    -exec bash -c '
        old_uuid=$1
        new_uuid=$2
        shift 2
        for path in "$@"; do
            dir=${path%/*}
            base=${path##*/}
            mv -- "$path" "$dir/${base//$old_uuid/$new_uuid}"
        done
    ' _ "$old_uuid" "$new_uuid" {} +

while read -r file; do
    sed -i "s/$old_uuid/$new_uuid/g" "$file"
done < <(grep -rl -- "$old_uuid" "$work_dir" || true)
