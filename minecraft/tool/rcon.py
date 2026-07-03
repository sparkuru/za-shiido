import argparse
import asyncio
import os
from pathlib import Path

from aiomcrcon import Client


DEFAULT_PORTS = [
    {"game_port": "9460", "rcon_port": 9461, "password": None},
    {"game_port": "9462", "rcon_port": 9463, "password": None},
    {"game_port": "9464", "rcon_port": 9465, "password": None},
    {"game_port": "9466", "rcon_port": 9467, "password": None},
    {"game_port": "9468", "rcon_port": 9469, "password": None},
]
DEFAULT_SERVER_ROOT = str(Path(__file__).resolve().parent.parent / "server")


def color(text: str = "", color_id: int = 2) -> str:
    """返回对应的控制台 ANSI 颜色。"""
    color_table = {
        0: "{}",
        1: "\033[1;30m{}\033[0m",
        2: "\033[1;31m{}\033[0m",
        3: "\033[1;32m{}\033[0m",
        4: "\033[1;33m{}\033[0m",
        5: "\033[1;34m{}\033[0m",
        6: "\033[1;35m{}\033[0m",
        7: "\033[1;36m{}\033[0m",
        8: "\033[1;37m{}\033[0m",
    }
    return color_table.get(color_id, "{}").format(text)


def parse_properties(path: Path) -> dict[str, str]:
    result = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = path.read_text(encoding="latin-1").splitlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def discover_servers(server_root: Path) -> list[dict[str, str | int | None]]:
    servers = []
    if not server_root.is_dir():
        return servers

    for properties_file in sorted(server_root.glob("*/server.properties")):
        properties = parse_properties(properties_file)
        rcon_port = properties.get("rcon.port")
        if not rcon_port:
            continue

        try:
            parsed_rcon_port = int(rcon_port)
        except ValueError:
            continue

        servers.append(
            {
                "game_port": properties.get("server-port", "?"),
                "rcon_port": parsed_rcon_port,
                "password": properties.get("rcon.password") or None,
            }
        )

    return sorted(servers, key=lambda item: int(item["rcon_port"]))


def password_for_port(
    port: int,
    servers: list[dict[str, str | int | None]],
    password_override: str | None,
) -> str | None:
    if password_override:
        return password_override

    for server in servers:
        if server["rcon_port"] == port:
            return server["password"]

    return None


async def send_command(host: str, port: int, password: str, command: str) -> str:
    try:
        client = Client(host, port, password)
        await client.connect()
        response = await client.send_cmd(command)
        await client.close()
        return str(response[0].strip())
    except Exception as exc:
        return color(f"port: {port} doesn't work: {exc}", 2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=9461,
        help="指定 RCON 端口，默认端口为 9461，可选端口为 9463 9465 9467 9469",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("RCON_HOST", "127.0.0.1"),
        help="指定 RCON 主机，默认读取 RCON_HOST 或使用 127.0.0.1",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("RCON_PASSWORD"),
        help="指定 RCON 密码，默认读取 RCON_PASSWORD 或匹配 server.properties",
    )
    parser.add_argument(
        "--server-root",
        default=os.environ.get("MINECRAFT_SERVER_DIR", DEFAULT_SERVER_ROOT),
        help="Minecraft server 根目录，默认读取 MINECRAFT_SERVER_DIR",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="要执行的 RCON 命令")
    return parser


async def print_result(host: str, server: dict[str, str | int | None], command: str) -> None:
    rcon_port = int(server["rcon_port"])
    password = server["password"]
    if not password:
        print(color(f"rcon password not found for port {rcon_port}", 2))
        print("-" * 40)
        return

    response = await send_command(host, rcon_port, str(password), command)
    print(
        f"game port: {color(str(server['game_port']), 3)}"
        f" - rcon port: {color(str(rcon_port), 2)}"
        f" - command: {color(command, 3)};\n"
        f"{color(response, 4)}\n"
        f"{'-' * 40}"
    )


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    command = " ".join(args.command).strip() or "list"
    discovered_servers = discover_servers(Path(args.server_root))

    if command == "list":
        servers = discovered_servers or DEFAULT_PORTS
        servers = [
            {
                **server,
                "password": password_for_port(
                    int(server["rcon_port"]), discovered_servers, args.password
                ),
            }
            for server in servers
        ]
        for server in servers:
            await print_result(args.host, server, command)
        return

    password = password_for_port(args.port, discovered_servers, args.password)
    if not password:
        parser.error(
            "RCON password not found. Set RCON_PASSWORD, pass --password, "
            "or make sure --server-root contains matching server.properties."
        )

    server = next(
        (
            item
            for item in discovered_servers
            if int(item["rcon_port"]) == int(args.port)
        ),
        {"game_port": str(args.port - 1), "rcon_port": args.port, "password": password},
    )
    await print_result(args.host, {**server, "password": password}, command)


if __name__ == "__main__":
    asyncio.run(main())
