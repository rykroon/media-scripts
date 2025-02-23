from argparse import ArgumentParser
from datetime import datetime
import json
import mimetypes
from pathlib import Path
import subprocess
from typing import NamedTuple

from PIL import Image as image, ExifTags as exif_tags



class ExifData(NamedTuple):
    date_time: datetime | None = None
    date_time_original: datetime | None = None
    date_time_digitized: datetime | None = None
    gps_latitude: float | None = None
    gps_longitude: float | None = None
    make: str | None = None
    model: str | None = None

    def get_dates(self) -> list[datetime]:
        return list(
            filter(
                None,
                (self.date_time, self.date_time_original, self.date_time_digitized),
            )
        )

    def has_gps_info(self) -> bool:
        return self.gps_latitude is not None and self.gps_longitude is not None

    def has_camera_info(self) -> bool:
        return self.make is not None and self.model is not None


def get_data_via_exiftool(f: Path) -> ExifData:
    """
    Get the dates from the EXIF data using exiftool.
    exiftool supports getting data for videos as well.
    The downside is that it is really slow.
    """
    cmd = [
        "exiftool",
        "-j",
        "-n",
        "-DateTimeOriginal",
        "-CreateDate",  # (called DateTimeDigitized by the EXIF spec.)
        "-ModifyDate",  # (called DateTime by the EXIF spec.)
        "-GPSLatitude",
        "-GPSLongitude",
        "-Make",
        "-Model",
        "-fast",
        str(f),
    ]
    completed_process = subprocess.run(cmd, capture_output=True, text=True)
    try:
        output = json.loads(completed_process.stdout)[0]
    except json.JSONDecodeError:
        return ExifData()

    date_time = output.get("ModifyDate", None)
    if date_time is not None:
        date_time = datetime.strptime(date_time, "%Y:%m:%d %H:%M:%S")

    date_time_original = output.get("DateTimeOriginal", None)
    if date_time_original is not None:
        date_time_original = datetime.strptime(date_time_original, "%Y:%m:%d %H:%M:%S")

    date_time_digitized = output.get("CreateDate", None)
    if date_time_digitized is not None:
        date_time_digitized = datetime.strptime(
            date_time_digitized, "%Y:%m:%d %H:%M:%S"
        )

    return ExifData(
        date_time=date_time,
        date_time_original=date_time_original,
        date_time_digitized=date_time_digitized,
        gps_latitude=output.get("GPSLatitude", None),
        gps_longitude=output.get("GPSLongitude", None),
        make=output.get("Make", None),
        model=output.get("Model", None),
    )


def get_data_via_pillow(f: Path) -> ExifData:
    """
    Get the dates from the EXIF data using Pillow.
    Pillow only supports images.
    """
    with image.open(f) as img:
        exif = img.getexif()

    basic_data = {exif_tags.TAGS[k]: v for k, v in exif.items() if k in exif_tags.TAGS}
    try:
        exif_data = {
            exif_tags.TAGS[k]: v
            for k, v in exif.get_ifd(exif_tags.IFD.Exif).items()
            if k in exif_tags.TAGS
        }
    except ValueError as e:
        print(f"Error: {e}, {f}")
        exif_data = {}

    gps_info = {
        exif_tags.GPSTAGS[k]: v
        for k, v in exif.get_ifd(exif_tags.IFD.GPSInfo).items()
        if k in exif_tags.GPSTAGS
    }

    date_time = basic_data.get("DateTime", None)
    if date_time is not None:
        date_time = datetime.strptime(date_time, "%Y:%m:%d %H:%M:%S")

    date_time_original = exif_data.get("DateTimeOriginal", None)
    if date_time_original is not None:
        date_time_original = datetime.strptime(date_time_original, "%Y:%m:%d %H:%M:%S")

    date_time_digitized = exif_data.get("DateTimeDigitized", None)
    if date_time_digitized is not None:
        date_time_digitized = datetime.strptime(
            date_time_digitized, "%Y:%m:%d %H:%M:%S"
        )

    return ExifData(
        date_time=date_time,
        date_time_original=date_time_original,
        date_time_digitized=date_time_digitized,
        gps_latitude=gps_info.get("GPSLatitude", None),
        gps_longitude=gps_info.get("GPSLongitude", None),
        make=basic_data.get("Make", None),
        model=basic_data.get("Model", None),
    )


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
    destination: Path,
    recursive: bool,
    gps_only: bool,
    camera_only: bool,
    dry_run: bool
):
    for f in source.iterdir():
        # Recurse into directories
        if recursive is True and f.is_dir():
            rename_files(
                source=f,
                destination=destination,
                recursive=recursive,
                gps_only=gps_only,
                camera_only=camera_only,
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

        # possible add back check for geo-tagging

        if type_.startswith("image"):
            exif_data = get_data_via_pillow(f)
        else:
            exif_data = get_data_via_exiftool(f)
        
        if gps_only is True and not exif_data.has_gps_info():
            continue

        if camera_only is True and not exif_data.has_camera_info():
            continue

        dates = exif_data.get_dates()
        dates.extend(get_dates_via_stat(f))

        if not dates:
            print(f"Could not get dates for {f.name}.")
            continue

        # Get the minimum time
        min_date = min(dates)

        # Create the new file name
        date_string = min_date.isoformat("_", "seconds").replace(":", "-")
        new_name = f"{date_string}{f.suffix.lower()}"

        new_file = destination / str(min_date.year) / new_name

        while new_file.exists():
            # If the file already exists, add a number to the end of the file name
            new_name_parts = new_file.stem.split("_")
            if len(new_name_parts) == 2:
                new_file = new_file.with_stem(f"{new_file.stem}_1")
            elif len(new_name_parts) == 3:
                new_file = new_file.with_stem(
                    f"{new_name_parts[0]}_{new_name_parts[1]}_{int(new_name_parts[2]) + 1}"
                )
            else:
                raise ValueError("Invalid file name.")

        print(f"{f} -> {new_file}")

        if dry_run is False:
            new_file.parent.mkdir(parents=True, exist_ok=True)  # create the parent directories
            f.rename(new_file)  # move the file to the destination


if __name__ == "__main__":
    parser = ArgumentParser()

    # Add arguments
    parser.add_argument("--src", type=Path, required=True, help="Source directory.")
    parser.add_argument(
        "--dest", type=Path, required=True, help="Destination directory."
    )
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="Recursively rename files."
    )
    parser.add_argument(
        "--gps-only", action="store_true", help="Only rename files with GPS data."
    )
    parser.add_argument(
        "--camera-only", action="store_true", help="Only rename files with camera data."
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not rename files.")

    ns = parser.parse_args()

    if not ns.src.is_dir():
        parser.error("Source must be a directory.")

    if ns.dest.exists() and not ns.dest.is_dir():
        parser.error("Destination must be a directory.")

    if ns.src == ns.dest:
        parser.error("Source and destination must be different directories.")

    if ns.recursive is True and ns.src in ns.dest.parents:
        parser.error("Destination cannot be a subdirectory of the source.")

    if ns.dry_run is False:
        result = input("Are you sure you want to rename the files? [yes/no]: ")
        if result != "yes":
            parser.exit(1)

    rename_files(
        source=ns.src,
        destination=ns.dest,
        recursive=ns.recursive,
        gps_only=ns.gps_only,
        camera_only=ns.camera_only,
        dry_run=ns.dry_run,
    )
