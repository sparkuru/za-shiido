#!/usr/bin/env bash
set -Eeuo pipefail

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC2034  # used by sourced .env defaults
workdir=$(cd "$script_dir/.." && pwd)

env_file="$script_dir/.env"

if [ ! -f "$env_file" ]; then
  printf 'Error: missing env file: %s\n' "$env_file" >&2
  printf 'Copy %s and adjust it before starting the server.\n' "$script_dir/.env.example" >&2
  exit 1
fi

set -o allexport
# shellcheck source=/dev/null
source "$env_file"
set +o allexport

: "${binary:?missing binary in $env_file}"
: "${port:?missing port in $env_file}"
: "${queryport:?missing queryport in $env_file}"
: "${hostname:?missing hostname in $env_file}"
: "${token:=}"
: "${password:=}"

exec "$binary" "Ministry?Scenario=Scenario_Ministry_Checkpoint_Security?MaxPlayers=10?port=$port?queryport=$queryport?password=$password" -hostname="$hostname" -GameStats -GSLTToken="$token" -Rcon -log -mutators=AllYouCanEat,BulletSponge,Vampirism
