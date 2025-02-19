from argparse import ArgumentParser
from pathlib import Path


def search_and_delete(
    term: str,
    source: Path,
    recursive: bool,
    case_insensitive: bool
):
    if len(term) < 3:
        print("Search term must be at least 3 characters long.")
        return

    if not source.is_dir():
        return

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

    search_and_delete(
        term=ns.term,
        source=ns.src,
        recursive=ns.recursive,
        case_insensitive=ns.case_insensitive
    )
