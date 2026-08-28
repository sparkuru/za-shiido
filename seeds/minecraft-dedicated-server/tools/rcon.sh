#!/usr/bin/zsh

work_dir=${0:A:h}
python_bin="$work_dir/venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
    python_bin=python3
fi

if [ "$#" -eq 0 ]; then
    set -- list
fi

"$python_bin" "$work_dir/rcon.py" "$@"
