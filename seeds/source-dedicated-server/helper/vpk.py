# -*- coding: utf-8 -*-

import argparse
import os
import posixpath
import struct
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterable

DEBUG_MODE = False

VPK_SIGNATURE = 0x55AA1234
DIR_ARCHIVE_INDEX = 0x7FFF
ENTRY_STRUCT = struct.Struct("<IHHIIH")
HEADER_STRUCT = struct.Struct("<III")
VERSION_TWO_HEADER_STRUCT = struct.Struct("<IIIIIII")
BUFFER_SIZE = 1024 * 1024


class CLIStyle:
    """CLI tool unified style config."""

    COLORS = {
        "TITLE": 7,
        "SUB_TITLE": 2,
        "CONTENT": 3,
        "EXAMPLE": 7,
        "WARNING": 4,
        "ERROR": 2,
    }

    @staticmethod
    def color(text: str = "", color: int = COLORS["CONTENT"]) -> str:
        """Unified color processing function."""
        if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
            return text

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
        return color_table[color].format(text)


class ColoredArgumentParser(argparse.ArgumentParser):
    """Argument parser with colorized help output."""

    def _format_action_invocation(self, action: argparse.Action) -> str:
        """Format option invocations with semantic colors."""
        if not action.option_strings:
            metavar_formatter = self._metavar_formatter(action, action.dest)
            metavar = metavar_formatter(1)[0]
            return str(metavar)

        parts = []
        if action.nargs == 0:
            parts.extend(
                CLIStyle.color(option_string, CLIStyle.COLORS["SUB_TITLE"])
                for option_string in action.option_strings
            )
        else:
            args_string = self._format_args(action, action.dest.upper())
            for option_string in action.option_strings:
                parts.append(
                    CLIStyle.color(
                        f"{option_string} {args_string}",
                        CLIStyle.COLORS["SUB_TITLE"],
                    )
                )
        return ", ".join(parts)

    def format_help(self) -> str:
        """Return colorized help text."""
        formatter = self._get_formatter()
        if self.description:
            formatter.add_text(
                CLIStyle.color(self.description, CLIStyle.COLORS["TITLE"])
            )
        formatter.add_usage(self.usage, self._actions, self._mutually_exclusive_groups)
        formatter.add_text(
            CLIStyle.color("\nOptional Arguments:", CLIStyle.COLORS["TITLE"])
        )
        for action_group in self._action_groups:
            formatter.start_section(action_group.title)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
        if self.epilog:
            formatter.add_text(self.epilog)
        return formatter.format_help()


@dataclass(frozen=True)
class VPKEntry:
    """Metadata for one file stored in a VPK."""

    path: str
    crc: int
    preload_data: bytes
    archive_index: int
    offset: int
    size: int


@dataclass(frozen=True)
class VPKHeader:
    """Parsed VPK header fields needed for extraction."""

    version: int
    header_size: int
    tree_size: int


class VPKArchive:
    """Read and extract files from a Valve Pak archive."""

    def __init__(self, vpk_path: Path, path_encoding: str) -> None:
        """Initialize an archive reader.
        ```python
        archive = VPKArchive(Path("pak01_dir.vpk"), "utf-8")

        return = None
        ```
        """
        self.vpk_path = vpk_path
        self.path_encoding = path_encoding
        self.header = self._read_header()

    def iter_entries(self) -> Iterable[VPKEntry]:
        """Yield archive entries from the VPK directory tree.
        ```python
        for entry in archive.iter_entries():
            output(entry.path)

        return = iterable of VPKEntry
        ```
        """
        with self.vpk_path.open("rb") as vpk_file:
            vpk_file.seek(self.header.header_size)
            while True:
                extension = self._read_cstring(vpk_file)
                if extension == "":
                    return
                yield from self._iter_paths(vpk_file, extension)

    def extract_all(self, output_dir: Path) -> int:
        """Extract all archive entries to a directory.
        ```python
        count = archive.extract_all(Path("/tmp/out"))

        return = number of extracted files
        ```
        """
        count = 0
        output_dir.mkdir(parents=True, exist_ok=True)
        for entry in self.iter_entries():
            self.extract_entry(entry, output_dir)
            count += 1
        return count

    def extract_entry(self, entry: VPKEntry, output_dir: Path) -> Path:
        """Extract one archive entry to a directory.
        ```python
        path = archive.extract_entry(entry, Path("/tmp/out"))

        return = extracted file path
        ```
        """
        output_path = self._safe_output_path(output_dir, entry.path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as output_file:
            if entry.preload_data:
                output_file.write(entry.preload_data)
            if entry.size > 0:
                self._copy_entry_data(entry, output_file)
        return output_path

    def _read_header(self) -> VPKHeader:
        """Read and validate the VPK header."""
        with self.vpk_path.open("rb") as vpk_file:
            header_data = vpk_file.read(VERSION_TWO_HEADER_STRUCT.size)

        if len(header_data) < HEADER_STRUCT.size:
            raise ValueError(f"Not a VPK file or truncated header: {self.vpk_path}")

        signature, version, tree_size = HEADER_STRUCT.unpack(
            header_data[: HEADER_STRUCT.size]
        )
        if signature != VPK_SIGNATURE:
            raise ValueError(f"Invalid VPK signature: {self.vpk_path}")
        if version == 1:
            return VPKHeader(
                version=version,
                header_size=HEADER_STRUCT.size,
                tree_size=tree_size,
            )
        if version == 2:
            if len(header_data) < VERSION_TWO_HEADER_STRUCT.size:
                raise ValueError(f"Truncated VPK v2 header: {self.vpk_path}")
            return VPKHeader(
                version=version,
                header_size=VERSION_TWO_HEADER_STRUCT.size,
                tree_size=tree_size,
            )
        raise ValueError(f"Unsupported VPK version {version}: {self.vpk_path}")

    def _iter_paths(
        self,
        vpk_file: BinaryIO,
        extension: str,
    ) -> Iterable[VPKEntry]:
        """Yield all entries for one extension group."""
        while True:
            directory = self._read_cstring(vpk_file)
            if directory == "":
                return
            yield from self._iter_names(vpk_file, extension, directory)

    def _iter_names(
        self,
        vpk_file: BinaryIO,
        extension: str,
        directory: str,
    ) -> Iterable[VPKEntry]:
        """Yield all entries for one extension and directory group."""
        while True:
            name = self._read_cstring(vpk_file)
            if name == "":
                return
            path = self._build_entry_path(directory, name, extension)
            yield self._read_entry(vpk_file, path)

    def _read_entry(self, vpk_file: BinaryIO, path: str) -> VPKEntry:
        """Read one entry metadata block and preload bytes."""
        metadata = vpk_file.read(ENTRY_STRUCT.size)
        if len(metadata) != ENTRY_STRUCT.size:
            raise ValueError(f"Truncated metadata for {path}")

        crc, preload_size, archive_index, offset, size, terminator = ENTRY_STRUCT.unpack(
            metadata
        )
        if terminator != 0xFFFF:
            raise ValueError(f"Invalid entry terminator for {path}")

        preload_data = vpk_file.read(preload_size)
        if len(preload_data) != preload_size:
            raise ValueError(f"Truncated preload data for {path}")

        return VPKEntry(
            path=path,
            crc=crc,
            preload_data=preload_data,
            archive_index=archive_index,
            offset=offset,
            size=size,
        )

    def _copy_entry_data(self, entry: VPKEntry, output_file: BinaryIO) -> None:
        """Copy entry file data to the output file."""
        archive_path = self._archive_path(entry.archive_index)
        with archive_path.open("rb") as archive_file:
            archive_file.seek(self._data_offset(entry))
            remaining = entry.size
            while remaining > 0:
                chunk = archive_file.read(min(BUFFER_SIZE, remaining))
                if not chunk:
                    raise ValueError(f"Truncated file data for {entry.path}")
                output_file.write(chunk)
                remaining -= len(chunk)

    def _data_offset(self, entry: VPKEntry) -> int:
        """Return the absolute file offset for an entry."""
        if entry.archive_index == DIR_ARCHIVE_INDEX:
            return self.header.header_size + self.header.tree_size + entry.offset
        return entry.offset

    def _archive_path(self, archive_index: int) -> Path:
        """Return the file path for an archive index."""
        if archive_index == DIR_ARCHIVE_INDEX:
            return self.vpk_path

        filename = self.vpk_path.name
        if filename.endswith("_dir.vpk"):
            archive_name = f"{filename[:-8]}_{archive_index:03d}.vpk"
            return self.vpk_path.with_name(archive_name)

        if archive_index == 0:
            return self.vpk_path

        raise ValueError(
            f"Multi-archive VPK requires a _dir.vpk input: {self.vpk_path}"
        )

    def _read_cstring(self, vpk_file: BinaryIO) -> str:
        """Read a NUL-terminated string from a VPK file."""
        data = bytearray()
        while True:
            byte = vpk_file.read(1)
            if byte == b"":
                raise ValueError(f"Unexpected end of VPK tree: {self.vpk_path}")
            if byte == b"\0":
                return data.decode(self.path_encoding)
            data.extend(byte)

    @staticmethod
    def _build_entry_path(directory: str, name: str, extension: str) -> str:
        """Build a normalized POSIX entry path from VPK tree names."""
        filename = name if extension == " " else f"{name}.{extension}"
        if directory == " ":
            return filename
        return posixpath.join(directory, filename)

    @staticmethod
    def _safe_output_path(output_dir: Path, entry_path: str) -> Path:
        """Return an output path after blocking unsafe archive paths."""
        pure_path = PurePosixPath(entry_path)
        if pure_path.is_absolute() or ".." in pure_path.parts:
            raise ValueError(f"Unsafe archive path: {entry_path}")

        output_path = output_dir.joinpath(*pure_path.parts)
        output_root = output_dir.resolve()
        resolved_output = output_path.resolve()
        if os.path.commonpath([str(output_root), str(resolved_output)]) != str(
            output_root
        ):
            raise ValueError(f"Unsafe archive path: {entry_path}")
        return output_path


def output(
    text: str,
    color: int = CLIStyle.COLORS["CONTENT"],
    error: bool = False,
) -> None:
    """Write styled terminal output.
    ```python
    output("Done")

    return = None
    ```
    """
    stream = sys.stderr if error else sys.stdout
    stream.write(f"{CLIStyle.color(text, color)}\n")


def create_example_text(
    script_name: str,
    examples: list[tuple[str, str]],
    notes: list[str] | None = None,
) -> str:
    """Create colorized argparse example text.
    ```python
    text = create_example_text("vpk.py", [("List files", "list file.vpk")])

    return = formatted help text
    ```
    """
    text = f"\n{CLIStyle.color('Examples:', CLIStyle.COLORS['SUB_TITLE'])}"
    for description, command in examples:
        text += f"\n  {CLIStyle.color(f'# {description}', CLIStyle.COLORS['EXAMPLE'])}"
        text += f"\n  {CLIStyle.color(f'{script_name} {command}', CLIStyle.COLORS['CONTENT'])}\n"
    if notes:
        text += f"\n{CLIStyle.color('Notes:', CLIStyle.COLORS['SUB_TITLE'])}"
        for note in notes:
            text += f"\n  {CLIStyle.color(f'- {note}', CLIStyle.COLORS['CONTENT'])}"
    return text


def list_entries(args: argparse.Namespace) -> int:
    """List file paths stored in a VPK.
    ```python
    status = list_entries(args)

    return = process exit code
    ```
    """
    archive = VPKArchive(Path(args.vpk_file), args.path_encoding)
    for entry in archive.iter_entries():
        output(entry.path)
    return 0


def extract_entries(args: argparse.Namespace) -> int:
    """Extract every file stored in a VPK.
    ```python
    status = extract_entries(args)

    return = process exit code
    ```
    """
    archive = VPKArchive(Path(args.vpk_file), args.path_encoding)
    count = archive.extract_all(Path(args.output_dir))
    output(
        f"Extracted {count} files to {args.output_dir}",
        CLIStyle.COLORS["SUB_TITLE"],
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the command line parser.
    ```python
    parser = build_parser()

    return = configured argument parser
    ```
    """
    script_name = Path(sys.argv[0]).name
    parser = ColoredArgumentParser(
        description="Extract Valve Pak files.",
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
    list_parser = subparsers.add_parser(
        "list",
        help=CLIStyle.color("List files in a VPK.", CLIStyle.COLORS["CONTENT"]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=create_example_text(
            script_name,
            [("List files", "list /tmp/addon.vpk")],
        ),
    )
    add_common_arguments(list_parser)
    list_parser.set_defaults(func=list_entries)

    extract_parser = subparsers.add_parser(
        "extract",
        help=CLIStyle.color("Extract files from a VPK.", CLIStyle.COLORS["CONTENT"]),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=create_example_text(
            script_name,
            [("Extract files", "extract /tmp/addon.vpk /tmp/addon-root")],
            ["For multi-part archives, pass the *_dir.vpk file."],
        ),
    )
    add_common_arguments(extract_parser)
    extract_parser.add_argument(
        "output_dir",
        metavar=CLIStyle.color("OUTPUT_DIR", CLIStyle.COLORS["SUB_TITLE"]),
        help=CLIStyle.color(
            "Directory that receives extracted files.",
            CLIStyle.COLORS["CONTENT"],
        ),
    )
    extract_parser.set_defaults(func=extract_entries)
    return parser


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments shared by subcommands.
    ```python
    add_common_arguments(parser)

    return = None
    ```
    """
    parser.add_argument(
        "vpk_file",
        metavar=CLIStyle.color("VPK_FILE", CLIStyle.COLORS["SUB_TITLE"]),
        help=CLIStyle.color("Input VPK file.", CLIStyle.COLORS["CONTENT"]),
    )
    parser.add_argument(
        "--path-encoding",
        default="utf-8",
        help=CLIStyle.color("Encoding used for VPK paths.", CLIStyle.COLORS["CONTENT"]),
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
