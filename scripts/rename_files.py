from argparse import ArgumentParser
from datetime import datetime
import json
import mimetypes
from pathlib import Path
import subprocess

from PIL import Image as image, ExifTags as exif_tags


"""
Simplify this scripts to only rename files (not move them)
"""


def get_dates_via_exiftool(f: Path) -> list[datetime]:
    """
    Get the dates from the EXIF data using exiftool.
    exiftool supports getting data for videos as well.
    The downside is that it is really slow.
    """
    cmd = [
        "exiftool",
        "-j",
        "-DateTimeOriginal",
        "-CreateDate", # (called DateTimeDigitized by the EXIF spec.)
        "-ModifyDate", # (called DateTime by the EXIF spec.)
        "-fast",
        str(f)
    ]
    completed_process = subprocess.run(cmd, capture_output=True, text=True)
    try:
        output = json.loads(completed_process.stdout)[0]
    except json.JSONDecodeError:
        return []

    dates = []
    for key in output:
        if "Date" in key:
            dates.append(datetime.strptime(output[key], "%Y:%m:%d %H:%M:%S"))
    
    return dates


def get_dates_via_pillow(f: Path):
    """
    Get the dates from the EXIF data using Pillow.
    Pillow only supports images.
    """
    with image.open(f) as img:
        idf0 = img.getexif()

    dates = []
    date_time = idf0.get(exif_tags.Base.DateTime, None)
    if date_time is not None:
        dates.append(datetime.strptime(date_time, "%Y:%m:%d %H:%M:%S"))

    try:
        exif = idf0.get_ifd(exif_tags.IFD.Exif)
    except ValueError as e:
        print(f"Error processing {f}: {e}")
        return []

    if exif:
        date_time_original = exif.get(exif_tags.Base.DateTimeOriginal, None)
        if date_time_original is not None:
            dates.append(datetime.strptime(date_time_original, "%Y:%m:%d %H:%M:%S"))

        date_time_digitized = exif.get(exif_tags.Base.DateTimeDigitized, None)
        if date_time_digitized is not None:
            dates.append(datetime.strptime(date_time_digitized, "%Y:%m:%d %H:%M:%S"))
    
    return dates


def get_dates_via_stat(f: Path) -> list[datetime]:
    """
    Get the dates from the file system using stat.
    """
    stat = f.stat()
    return [
        datetime.fromtimestamp(stat.st_atime),
        datetime.fromtimestamp(stat.st_ctime),
        datetime.fromtimestamp(stat.st_mtime),
    ]


def rename_files(
    source: Path,
    recursive: bool,
    exif_only: bool,
    dry_run: bool,
):
    if not source.is_dir():
        return

    for f in source.iterdir():
        # Recurse into directories
        if recursive is True and f.is_dir():
            rename_files(
                source=f,
                recursive=recursive,
                exif_only=exif_only,
                dry_run=dry_run,
            )

        if not f.is_file():
            continue

        # Skip files that are not images or videos
        type_, _ = mimetypes.guess_type(f)
        if type_ is None:
            continue

        if not type_.startswith("image") and not type_.startswith("video"):
            continue

        if type_.startswith("image"):
            dates = get_dates_via_pillow(f)
        else:
            dates = get_dates_via_exiftool(f)
        
        if exif_only is True and not dates:
            print(f"Could not find date for {f.name}.")
            continue

        if not dates:
            dates = get_dates_via_stat(f)

        # Get the minimum time
        min_date = min(dates)

        # Create the new file name
        date_string = min_date.isoformat("_", "seconds").replace(":", "-")
        new_name = f"{date_string}{f.suffix.lower()}"

        if f.name == new_name:
            # Skip if the name is the same
            continue

        print(f"{f.name} => {new_name}.")

        if dry_run is False:
            # add old name to user comment?
            f.rename(f.with_name(new_name))


if __name__ == "__main__":
    parser = ArgumentParser()

    # Add arguments
    parser.add_argument("--src", type=Path, default=Path.cwd())
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-e", "--exif-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    ns = parser.parse_args()

    rename_files(
        source=ns.src,
        recursive=ns.recursive,
        exif_only=ns.exif_only,
        dry_run=ns.dry_run,
    )
