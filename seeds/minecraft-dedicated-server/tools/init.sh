#!/usr/bin/zsh

init_name="S3iUqaO7iUwlzKu" # 不要改这个
script_dir=${0:A:h}
minecraft_path=${MINECRAFT_PATH:-${script_dir:h}}
server_dir=${MINECRAFT_SERVER_DIR:-$minecraft_path/server}
init_dir="$script_dir/init"
package_name=""
action=""

usage() {
    echo "Usage: ./init.sh --package_name a_minecraft_server --action [show/run]"
}

validate_package_name() {
    if [[ -z "$package_name" ]]; then
        echo "Missing --package_name"
        usage
        exit 1
    fi

    if [[ ! "$package_name" =~ '^[A-Za-z0-9._-]+$' ]]; then
        echo "Invalid package name: $package_name"
        echo "Only letters, numbers, dot, underscore, and hyphen are supported."
        exit 1
    fi
}

generate_rcon_password() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 24
    elif command -v uuidgen >/dev/null 2>&1; then
        uuidgen | tr -d '-'
    else
        LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 48
    fi
}

escape_sed_replacement() {
    printf '%s' "$1" | sed -e 's/[\/&]/\\&/g'
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --package_name)
            package_name="$2"
            shift 2 # 移过参数名和参数值
            ;;
        --action)
            action="$2"
            shift 2 # 移过参数名和参数值
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# 替换文件内容的函数
replace_contents() {
    target_dir=$1
    init_name=$2
    package_name=$3
    rcon_password=$4
    server_dir=$5
    server_dir_escaped=$(escape_sed_replacement "$server_dir")
    find "$target_dir" -type f -exec sed -i \
        -e "s/$init_name/$package_name/g" \
        -e "s/__RCON_PASSWORD__/$rcon_password/g" \
        -e "s/__SERVER_DIR__/$server_dir_escaped/g" {} +
}

# 根据action执行相应操作
if [ "$action" = "show" ]; then
    validate_package_name
    echo "cp -r $init_dir/* $server_dir/$package_name"
    echo "cd $server_dir/$package_name"
    echo "find . -name \"*$init_name*\" -exec rename 's/$init_name/$package_name/' {} +"
    echo "replace $init_name with $package_name in copied template files"
    echo "replace __RCON_PASSWORD__ with a generated per-server password"
    echo "replace __SERVER_DIR__ with $server_dir"
    exit
elif [ "$action" = "run" ]; then
    validate_package_name
    target_dir="$server_dir/$package_name"
    rcon_password=$(generate_rcon_password)
    if [ ! -d "$target_dir" ]; then
        mkdir -p "$target_dir"
    fi
    cp -r "$init_dir"/. "$target_dir"
    cd "$target_dir" || exit 1
    find . -depth -name "*$init_name*" -type f -exec bash -c '
        init_name=$1
        package_name=$2
        shift 2
        for path in "$@"; do
            dir=${path%/*}
            base=${path##*/}
            mv -- "$path" "$dir/${base//$init_name/$package_name}"
        done
    ' _ "$init_name" "$package_name" {} +
    replace_contents "$target_dir" "$init_name" "$package_name" "$rcon_password" "$server_dir"
    exec "$script_dir/static.sh" "$package_name"
else
    usage
    exit
fi
