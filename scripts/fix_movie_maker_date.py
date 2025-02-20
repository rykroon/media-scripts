from argparse import ArgumentParser
from datetime import datetime
import mimetypes
from pathlib import Path

from PIL import Image, ExifTags as exiftags


"""
This script is specifically for Movie Maker images that have a different
format for the DateTime tag in the EXIF data.
"""


def fix_movie_maker_date_time(source: Path, recursive: bool, dry_run: bool):
    assert source.is_dir(), "Not a Directory."

    for f in source.iterdir():
        # Recurse into directories
        if recursive is True and f.is_dir():
            fix_movie_maker_date_time(source=f, recursive=recursive, dry_run=dry_run)

        if not f.is_file():
            continue

        type_, _ = mimetypes.guess_type(f)
        if type_ is None:
            continue

        if not type_.startswith("image"):
            continue

        with Image.open(f) as img:
            exif = img.getexif()

            if exiftags.Base.Software not in exif:
                continue

            if "Movie Maker" not in exif[exiftags.Base.Software]:
                continue

            if exiftags.Base.DateTime not in exif:
                continue

            try:
                datetime.strptime(
                    exif[exiftags.Base.DateTime],
                    "%Y:%m:%d %H:%M:%S",
                )
            except ValueError:
                date_string = exif[exiftags.Base.DateTime]
                if len(date_string) > 24:
                    date_string = date_string[:24]

                date_time = datetime.strptime(date_string, "%a %b %d %H:%M:%S %Y")
                print(
                    f'File: {f.name} - "{exif[exiftags.Base.DateTime]}" => "{date_time}"'
                )

                if dry_run is False:
                    exif[exiftags.Base.DateTime] = date_time.strftime(
                        "%Y:%m:%d %H:%M:%S"
                    )
                    img.save(f, exif=exif)


if __name__ == "__main__":
    parser = ArgumentParser()

    # Add arguments
    parser.add_argument("--src", type=Path, default=Path.cwd())
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    ns = parser.parse_args()

    # Make sure directories are Path objects and
    # are relative to the current working directory
    ns.src = Path.cwd() / ns.src

    fix_movie_maker_date_time(
        source=ns.src,
        recursive=ns.recursive,
        dry_run=ns.dry_run,
    )
