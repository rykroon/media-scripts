
from argparse import ArgumentParser
from datetime import datetime
import mimetypes
from pathlib import Path

from PIL import Image
from PIL.ExifTags import Base as ExifTags


"""
This script is specifically for Movie Maker images that have a different
format for the DateTime tag in the EXIF data.
"""


def fix_movie_maker_date_time(source: Path, recursive: bool, apply_changes: bool):
    assert source.is_dir(), "Not a Directory."

    for f in source.iterdir():
        # Recurse into directories
        if f.is_dir() and recursive is True:
            fix_movie_maker_date_time(f, recursive, apply_changes)

        if not f.is_file():
            continue
    
        mime_type, _ = mimetypes.guess_type(f)
        if mime_type is None:
            continue

        if not mime_type.startswith("image"):
            continue

        with Image.open(f) as img:
            exif = img.getexif()

            if ExifTags.Software not in exif:
                continue

            if "Movie Maker" not in exif[ExifTags.Software]:
                continue

            if ExifTags.DateTime not in exif:
                continue

            try:
                datetime.strptime(
                    exif[ExifTags.DateTime], "%Y:%m:%d %H:%M:%S",
                )
            except ValueError:
                date_string = exif[ExifTags.DateTime]
                if len(date_string) > 24:
                    date_string = date_string[:24]

                date_time = datetime.strptime(date_string, "%a %b %d %H:%M:%S %Y")
                print(f'File: {f.name} - "{exif[ExifTags.DateTime]}" => "{date_time}"')

                if apply_changes is True:
                    exif[ExifTags.DateTime] = date_time.strftime("%Y:%m:%d %H:%M:%S")
                    img.save(f, exif=exif)


if __name__ == "__main__":
    parser = ArgumentParser()

    # Add arguments
    parser.add_argument("--src", type=str, default=".")
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-a", "--apply", action="store_true")
    ns = parser.parse_args()

    # Make sure directories are Path objects and
    # are relative to the current working directory
    ns.src = Path.cwd() / ns.src

    fix_movie_maker_date_time(
        source=ns.src,
        recursive=ns.recursive,
        apply_changes=ns.apply,
    )
