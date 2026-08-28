#!/usr/bin/env zsh

set -e
set -u
set -o pipefail

work_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$work_dir"

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
        echo "Copy $work_dir/.env.example and adjust it before starting the server." >&2
        exit 1
    fi

    set -o allexport
    source "$env_file"
    set +o allexport
}

ensure_server_config() {
    local source_cfg_dir="$work_dir/../left4dead2/cfg"
    local target_game_dir="$left4dead2_dir/left4dead2"
    local target_cfg_dir="$target_game_dir/cfg"
    local target_server_cfg="$target_cfg_dir/server.cfg"

    if [[ -f "$target_server_cfg" ]]; then
        return 0
    fi

    if [[ ! -f "$source_cfg_dir/server.cfg" ]]; then
        echo "Error: source server config does not exist: $source_cfg_dir/server.cfg" >&2
        exit 1
    fi

    if [[ -e "$target_cfg_dir" && ! -L "$target_cfg_dir" ]]; then
        echo "Error: target cfg path exists but has no server.cfg: $target_cfg_dir" >&2
        exit 1
    fi

    mkdir -p -- "$target_game_dir"
    ln -sfn -- "$source_cfg_dir" "$target_game_dir"
}

left4dead2_dir="$(find_path "left4dead2")"
load_env

: "${binary_path:?missing binary_path in $env_file}"
: "${game_name:?missing game_name in $env_file}"
: "${server_ip:?missing server_ip in $env_file}"
: "${server_config:?missing server_config in $env_file}"
: "${map_file:?missing map_file in $env_file}"

ensure_server_config

"$binary_path" \
    -game "$game_name" \
    -condebug \
    +ip "$server_ip" \
    -insecure \
    -nomaster \
    -debug \
    +exec "$server_config" \
    +map "$(cat "$map_file")"

# -game	            指定游戏是left4dead2
# -insecure	        关闭VAC，建议关，不然可能有冲突
# +hostport	        对应开放的端口，不写就默认是27015
# -condebug	        输出debug信息
# -nomaster	        隐藏服务器连接
# -maxplayers num	最大游戏人数
# +exec server.cfg	按照写好的server.cfg脚本执行
# +map xxx	        指定一张地图启动
