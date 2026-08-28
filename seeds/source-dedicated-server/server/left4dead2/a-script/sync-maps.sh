#!/usr/bin/env zsh

set -e
set -u
set -o pipefail

script_name="${0:t}"
force_overwrite=false

usage() {
    printf 'Usage: %s [--force] [--help]\n\n' "$script_name"
    printf 'Sync L4D2 addon maps from VPK packages or the configured zip package.\n\n'
    printf 'Options:\n'
    printf '  -f, --force   Process VPK packages even when target maps already exist.\n'
    printf '                This can overwrite files under target_dir, including maps/*.bsp.\n'
    printf '  -h, --help    Show this help.\n\n'
    printf 'VPK behavior:\n'
    printf '  The script checks vpk_search_dir, defaulting to dirname(zip_path).\n'
    printf '  Without --force, a VPK is skipped when any package map already exists\n'
    printf '  in target_dir/maps.\n'
}

fail() {
    printf '[sync-maps] Error: %s\n' "$*" >&2
    exit 1
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -f|--force)
                force_overwrite=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            --)
                shift
                break
                ;;
            -*)
                fail "Unknown option: $1"
                ;;
            *)
                fail "Unexpected argument: $1"
                ;;
        esac
    done
}

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
        fail "Missing env file: $env_file. Copy .env.example and adjust it before syncing maps."
    fi

    set -o allexport
    source "$env_file"
    set +o allexport
}

parse_args "$@"

work_dir=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$work_dir"

seed_dir="$(cd -- "$work_dir/../../.." && pwd)"
left4dead2_dir="$(find_path "left4dead2")" ||
    fail "Could not find parent directory named left4dead2 from $work_dir."
load_env

: "${zip_path:?missing zip_path in $env_file}"
: "${target_dir:?missing target_dir in $env_file}"
: "${maps_index_path:?missing maps_index_path in $env_file}"

vpk_search_dir="${vpk_search_dir:-$(dirname -- "$zip_path")}"
l4d2_helper_path="$seed_dir/helper/l4d2.py"

command -v python3 >/dev/null 2>&1 || fail "python3 is not installed or not in PATH."
[[ -f "$l4d2_helper_path" ]] || fail "L4D2 helper does not exist: $l4d2_helper_path"

sync_args=(
    sync
    --zip-path "$zip_path"
    --vpk-search-dir "$vpk_search_dir"
    --target-dir "$target_dir"
    --maps-index-path "$maps_index_path"
)

if [[ "$force_overwrite" == true ]]; then
    sync_args+=(--force)
fi

python3 "$l4d2_helper_path" "${sync_args[@]}"
