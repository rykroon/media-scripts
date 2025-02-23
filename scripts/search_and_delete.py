from argparse import ArgumentParser
from pathlib import Path


def search_and_delete(source: Path, term: str, recursive: bool, case_insensitive: bool):
    for f in source.iterdir():
        if recursive is True and f.is_dir():
            search_and_delete(source=f, term=term, recursive=recursive)

        if not f.is_file():
            continue

        if (not case_insensitive and term in f.name) or (
            case_insensitive and term.lower() in f.name.lower()
        ):
            result = input(f"Delete file {f.name}? [y/n]: ")
            if result == "y":
                f.unlink()


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-t", "--term", type=str, required=True)
    parser.add_argument("-s", "--src", type=Path, default=Path.cwd())
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-i", "--case-insensitive", action="store_true")
    ns = parser.parse_args()

    if len(ns.term) < 3:
        parser.error("Search term must be at least 3 characters long.")

    if not ns.src.is_dir():
        parser.error("Source must be a directory.")

    search_and_delete(
        source=ns.src,
        term=ns.term,
        recursive=ns.recursive,
        case_insensitive=ns.case_insensitive,
    )
