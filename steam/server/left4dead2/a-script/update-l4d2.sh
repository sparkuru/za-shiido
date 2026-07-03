#!/usr/bin/env zsh

set -e
set -u
set -o pipefail

find_path() {
    current_dir=$(pwd)
	if [ $# -eq 1 ]; then
		target_dir_name=$1
	else
		target_dir_name="$leader_path_name"
	fi

    while [[ "$current_dir" != "/" ]]; do
        base_name=$(basename "$current_dir")
        if [[ "$base_name" == "$target_dir_name" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir=$(dirname "$current_dir")
    done
    return 1
}

load_env() {
    env_file="$work_dir/.env"

    if [ ! -f "$env_file" ]; then
        echo "Error: missing env file: $env_file" >&2
        echo "Copy $work_dir/.env.example and adjust it before updating the server." >&2
        exit 1
    fi

    set -o allexport
    source "$env_file"
    set +o allexport
}

work_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$work_dir"

steam_dir="$(find_path "steam")"
left4dead2_dir="$(find_path "left4dead2")"
load_env

: "${steamcmd_binary:?missing steamcmd_binary in $env_file}"
: "${force_install_dir:?missing force_install_dir in $env_file}"
: "${steam_login:?missing steam_login in $env_file}"
: "${steam_app_id:?missing steam_app_id in $env_file}"

"$steamcmd_binary" \
	+force_install_dir "$force_install_dir" \
	+login "$steam_login" \
	+App_update "$steam_app_id" \
	validate \
	+quit
