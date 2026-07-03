# -*- coding: utf-8 -*-

import argparse
import re
import shutil
import sys
import tempfile
import traceback
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

try:
    from .vpk import CLIStyle, ColoredArgumentParser, VPKArchive, create_example_text, output
except ImportError:
    from vpk import CLIStyle, ColoredArgumentParser, VPKArchive, create_example_text, output

DEBUG_MODE = False

ADDON_TITLE_PATTERN = re.compile(
    r'^[\s]*"?[Aa][Dd][Dd][Oo][Nn][Tt][Ii][Tt][Ll][Ee]"?[\s]+"([^"]+)"'
)
VPK_PART_PATTERN = re.compile(r"_[0-9]{3}\.vpk$")


@dataclass(frozen=True)
class SyncConfig:
    """L4D2 addon sync configuration."""

    zip_path: Path
    vpk_search_dir: Path
    target_dir: Path
    maps_index_path: Path
    force: bool


@dataclass(frozen=True)
class AddonPackage:
    """Extracted addon package context."""

    package_path: Path
    extract_dir: Path
    source_dir: Path


def validate_zip_paths(zip_path: Path) -> None:
    """Validate that a zip package does not contain unsafe paths.
    ```python
    validate_zip_paths(Path("/tmp/root.zip"))

    return = None
    ```
    """
    with zipfile.ZipFile(zip_path) as zip_file:
        for zip_info in zip_file.infolist():
            entry_path = PurePosixPath(zip_info.filename)
            if zip_info.filename == "" or entry_path.is_absolute():
                raise ValueError(f"Unsafe path in zip: {zip_info.filename}")
            if ".." in entry_path.parts:
                raise ValueError(f"Unsafe path in zip: {zip_info.filename}")


def extract_zip_package(zip_path: Path, extract_dir: Path) -> None:
    """Extract a validated zip package.
    ```python
    extract_zip_package(Path("/tmp/root.zip"), Path("/tmp/out"))

    return = None
    ```
    """
    validate_zip_paths(zip_path)
    with zipfile.ZipFile(zip_path) as zip_file:
        zip_file.extractall(extract_dir)


def detect_source_dir(extract_dir: Path) -> Path:
    """Detect the addon root inside an extracted package.
    ```python
    source_dir = detect_source_dir(Path("/tmp/addon"))

    return = addon root path
    ```
    """
    if is_addon_root(extract_dir):
        return extract_dir

    root_dir = extract_dir / "root"
    if root_dir.is_dir() and is_addon_root(root_dir):
        return root_dir

    raise ValueError(
        "Could not find a valid addon root. "
        "Expected maps/materials/models/addoninfo.txt at package root or under root/."
    )


def is_addon_root(path: Path) -> bool:
    """Return whether a directory looks like an L4D2 addon root.
    ```python
    result = is_addon_root(Path("/tmp/addon"))

    return = boolean
    ```
    """
    return (
        (path / "addoninfo.txt").exists()
        or (path / "maps").is_dir()
        or (path / "materials").is_dir()
        or (path / "models").is_dir()
    )


def detect_addon_title(source_dir: Path, fallback_name: str) -> str:
    """Read an addon title from addoninfo.txt when available.
    ```python
    title = detect_addon_title(Path("/tmp/addon"), "addon.vpk")

    return = addon title
    ```
    """
    addoninfo_path = source_dir / "addoninfo.txt"
    if not addoninfo_path.is_file():
        return fallback_name

    with addoninfo_path.open("r", encoding="utf-8", errors="replace") as addon_file:
        for line in addon_file:
            line_without_comment = line.split("//", 1)[0]
            match = ADDON_TITLE_PATTERN.search(line_without_comment)
            if match:
                return match.group(1)

    return fallback_name


def source_map_names(source_dir: Path) -> list[str]:
    """Return map names from an extracted addon root.
    ```python
    names = source_map_names(Path("/tmp/addon"))

    return = sorted map names without extension
    ```
    """
    maps_dir = source_dir / "maps"
    if not maps_dir.is_dir():
        return []
    return sorted(path.stem for path in maps_dir.glob("*.bsp") if path.is_file())


def vpk_map_names(vpk_path: Path) -> list[str]:
    """Return L4D2 map names listed inside a VPK package.
    ```python
    names = vpk_map_names(Path("/tmp/addon.vpk"))

    return = sorted map names without extension
    ```
    """
    archive = VPKArchive(vpk_path, "utf-8")
    map_names = []
    for entry in archive.iter_entries():
        entry_path = PurePosixPath(entry.path)
        if len(entry_path.parts) == 2 and entry_path.parts[0] == "maps":
            if entry_path.suffix == ".bsp":
                map_names.append(entry_path.stem)
    return sorted(map_names)


def existing_target_maps(target_dir: Path, map_names: Iterable[str]) -> list[str]:
    """Return maps already present in the target game directory.
    ```python
    existing = existing_target_maps(Path("/srv/l4d2"), ["c1m1_hotel"])

    return = existing map names
    ```
    """
    existing_names = []
    for map_name in map_names:
        if (target_dir / "maps" / f"{map_name}.bsp").exists():
            existing_names.append(map_name)
    return existing_names


def append_maps_index(
    maps_index_path: Path,
    addon_title: str,
    map_names: list[str],
) -> None:
    """Append one addon and its maps to the maps index.
    ```python
    append_maps_index(Path("maps.txt"), "Addon", ["map_a"])

    return = None
    ```
    """
    if not map_names:
        output("No .bsp map files found in addon package. Skipping maps.txt update.")
        return

    if maps_index_path.is_file() and addon_title in maps_index_path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        output(f"Maps index already contains package: {addon_title}")
        return

    maps_index_path.parent.mkdir(parents=True, exist_ok=True)
    needs_blank_line = (
        maps_index_path.is_file() and maps_index_path.stat().st_size > 0
    )
    with maps_index_path.open("a", encoding="utf-8") as maps_index_file:
        if needs_blank_line:
            maps_index_file.write("\n")
        maps_index_file.write(f"{addon_title}\n")
        for index, map_name in enumerate(map_names):
            branch = "└──" if index == len(map_names) - 1 else "├──"
            maps_index_file.write(f"{branch} {map_name}\n")

    output(f"Updated maps index: {maps_index_path} ({len(map_names)} map entries).")


def sync_directory(source_dir: Path, target_dir: Path) -> int:
    """Copy extracted addon files into the target game directory.
    ```python
    count = sync_directory(Path("/tmp/addon"), Path("/srv/l4d2"))

    return = copied file count
    ```
    """
    copied_count = 0
    for source_path in source_dir.rglob("*"):
        if source_path.is_dir():
            continue
        relative_path = source_path.relative_to(source_dir)
        target_path = target_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        copied_count += 1
    return copied_count


def sync_extracted_package(config: SyncConfig, addon_package: AddonPackage) -> None:
    """Sync one extracted addon package into the target directory.
    ```python
    sync_extracted_package(config, addon_package)

    return = None
    ```
    """
    map_names = source_map_names(addon_package.source_dir)
    addon_title = detect_addon_title(
        addon_package.source_dir,
        addon_package.package_path.name,
    )

    if not any(path.is_file() for path in addon_package.source_dir.rglob("*")):
        raise ValueError("Addon package contains no files to sync.")

    output(f"Addon root detected: {addon_package.source_dir}")
    output(f"Addon title detected: {addon_title}")
    output(f"Syncing new addon files into: {config.target_dir}")
    copied_count = sync_directory(addon_package.source_dir, config.target_dir)
    output(f"Copied {copied_count} files.")
    append_maps_index(config.maps_index_path, addon_title, map_names)


def iter_vpk_package_paths(vpk_search_dir: Path) -> Iterable[Path]:
    """Yield top-level VPK package paths from a search directory.
    ```python
    paths = list(iter_vpk_package_paths(Path("/tmp")))

    return = iterable of VPK paths
    ```
    """
    if not vpk_search_dir.is_dir():
        return

    for vpk_path in sorted(vpk_search_dir.glob("*.vpk")):
        if VPK_PART_PATTERN.search(vpk_path.name):
            continue
        yield vpk_path


def should_skip_vpk_package(config: SyncConfig, vpk_path: Path) -> bool:
    """Return whether a VPK should be skipped because maps already exist.
    ```python
    skip = should_skip_vpk_package(config, Path("/tmp/addon.vpk"))

    return = boolean
    ```
    """
    existing_maps = existing_target_maps(config.target_dir, vpk_map_names(vpk_path))
    if not existing_maps:
        return False

    if config.force:
        output(
            "Force enabled. Existing target maps may be overwritten: "
            f"{', '.join(existing_maps)}"
        )
        return False

    output(
        "Skipping VPK package because target maps already exist: "
        f"{vpk_path} ({', '.join(existing_maps)}). Use --force to overwrite."
    )
    return True


def sync_vpk_packages(config: SyncConfig) -> bool:
    """Sync unprocessed VPK packages from the configured search directory.
    ```python
    processed = sync_vpk_packages(config)

    return = whether any VPK package was found
    ```
    """
    found_vpk = False
    for vpk_path in iter_vpk_package_paths(config.vpk_search_dir):
        found_vpk = True
        if should_skip_vpk_package(config, vpk_path):
            continue

        with tempfile.TemporaryDirectory(
            prefix="l4d2-vpk-root.",
        ) as extract_dir_name:
            extract_dir = Path(extract_dir_name)
            output(f"Extracting VPK package: {vpk_path}")
            archive = VPKArchive(vpk_path, "utf-8")
            archive.extract_all(extract_dir)
            source_dir = detect_source_dir(extract_dir)
            addon_package = AddonPackage(vpk_path, extract_dir, source_dir)
            sync_extracted_package(config, addon_package)

    return found_vpk


def sync_zip_package(config: SyncConfig) -> None:
    """Sync the configured zip package using the legacy flow.
    ```python
    sync_zip_package(config)

    return = None
    ```
    """
    if not config.zip_path.is_file():
        raise FileNotFoundError(config.zip_path)
    if config.zip_path.stat().st_size == 0:
        raise ValueError(f"Zip file is empty: {config.zip_path}")

    with tempfile.TemporaryDirectory(prefix="l4d2-zip-root.") as extract_dir_name:
        extract_dir = Path(extract_dir_name)
        output(f"Checking zip package: {config.zip_path}")
        output("Extracting package to a temporary directory.")
        extract_zip_package(config.zip_path, extract_dir)
        source_dir = detect_source_dir(extract_dir)
        addon_package = AddonPackage(config.zip_path, extract_dir, source_dir)
        sync_extracted_package(config, addon_package)


def sync_packages(config: SyncConfig) -> int:
    """Sync VPK packages when present, otherwise sync the configured zip package.
    ```python
    status = sync_packages(config)

    return = process exit code
    ```
    """
    if not config.target_dir.is_dir():
        raise ValueError(f"Target directory does not exist: {config.target_dir}")

    if sync_vpk_packages(config):
        output("Done.")
        return 0

    sync_zip_package(config)
    output("Done.")
    return 0


def build_sync_config(args: argparse.Namespace) -> SyncConfig:
    """Build sync configuration from CLI arguments.
    ```python
    config = build_sync_config(args)

    return = sync configuration
    ```
    """
    vpk_search_dir = Path(args.vpk_search_dir)
    return SyncConfig(
        zip_path=Path(args.zip_path),
        vpk_search_dir=vpk_search_dir,
        target_dir=Path(args.target_dir),
        maps_index_path=Path(args.maps_index_path),
        force=bool(args.force),
    )


def run_sync(args: argparse.Namespace) -> int:
    """Run the sync subcommand.
    ```python
    status = run_sync(args)

    return = process exit code
    ```
    """
    return sync_packages(build_sync_config(args))


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser.
    ```python
    parser = build_parser()

    return = configured argument parser
    ```
    """
    script_name = Path(sys.argv[0]).name
    parser = ColoredArgumentParser(
        description="Manage Left 4 Dead 2 addon packages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help=CLIStyle.color(
            "Show debug tracebacks on errors.",
            CLIStyle.COLORS["CONTENT"],
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    sync_parser = subparsers.add_parser(
        "sync",
        help=CLIStyle.color("Sync addon packages.", CLIStyle.COLORS["CONTENT"]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=create_example_text(
            script_name,
            [
                (
                    "Sync VPKs from /tmp or fall back to root.zip",
                    "sync --zip-path /tmp/root.zip --vpk-search-dir /tmp "
                    "--target-dir /srv/l4d2/left4dead2 --maps-index-path maps.txt",
                ),
                (
                    "Force overwrite existing maps",
                    "sync --force --zip-path /tmp/root.zip --vpk-search-dir /tmp "
                    "--target-dir /srv/l4d2/left4dead2 --maps-index-path maps.txt",
                ),
            ],
            [
                "VPK packages are skipped when their maps already exist unless --force is set.",
                "The configured zip package is used only when no top-level VPK package is found.",
            ],
        ),
    )
    add_sync_arguments(sync_parser)
    sync_parser.set_defaults(func=run_sync)
    return parser


def add_sync_arguments(parser: argparse.ArgumentParser) -> None:
    """Add sync subcommand arguments.
    ```python
    add_sync_arguments(parser)

    return = None
    ```
    """
    parser.add_argument(
        "--zip-path",
        required=True,
        help=CLIStyle.color("Legacy zip package path.", CLIStyle.COLORS["CONTENT"]),
    )
    parser.add_argument(
        "--vpk-search-dir",
        required=True,
        help=CLIStyle.color(
            "Directory containing VPK packages.",
            CLIStyle.COLORS["CONTENT"],
        ),
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help=CLIStyle.color("L4D2 game target directory.", CLIStyle.COLORS["CONTENT"]),
    )
    parser.add_argument(
        "--maps-index-path",
        required=True,
        help=CLIStyle.color("maps.txt index path.", CLIStyle.COLORS["CONTENT"]),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=CLIStyle.color(
            "Process VPK packages even when target maps already exist.",
            CLIStyle.COLORS["CONTENT"],
        ),
    )


def run(args: argparse.Namespace) -> int:
    """Run the selected subcommand.
    ```python
    status = run(args)

    return = process exit code
    ```
    """
    return int(args.func(args))


def main() -> int:
    """Main program logic.
    ```python
    status = main()

    return = process exit code
    ```
    """
    global DEBUG_MODE

    parser = build_parser()
    args = parser.parse_args()
    DEBUG_MODE = bool(args.log)

    try:
        return run(args)
    except FileNotFoundError as error:
        output(
            f"Error: file not found: {error.filename}",
            CLIStyle.COLORS["ERROR"],
            True,
        )
        return 1
    except Exception as error:
        if DEBUG_MODE:
            traceback.print_exc()
        output(f"Error: {error}", CLIStyle.COLORS["ERROR"], True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
