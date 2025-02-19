from argparse import ArgumentParser
from datetime import datetime
import json
import mimetypes
from pathlib import Path
import string
import subprocess

from PIL import Image
from PIL.ExifTags import Base as ExifTags, GPS


PUNCTUATIONS = "".join([p for p in string.punctuation if p not in ("-", "_")])
TRANS_TABLE = str.maketrans(" ", "-", PUNCTUATIONS)


def get_exif_data_for_video(f: Path):
    cmd = ["exiftool", "-j", str(f)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    else:
        return metadata[0] if metadata else None


def get_exif_data_for_image(f: Path):
    with Image.open(f) as img:
        try:
            exif_data = img._getexif()
        except AttributeError:
            exif_data = None

    if exif_data is not None:
        exif_data = {
            ExifTags(tag).name: v for tag, v in exif_data.items() if tag in ExifTags
        }
        if "GPSInfo" in exif_data:
            gps_info = exif_data.pop("GPSInfo")
            exif_data.update(
                {GPS(tag).name: v for tag, v in gps_info.items() if tag in GPS}
            )

    return exif_data


def has_gps_info(exif_data):
    if "GPSLatitude" not in exif_data:
        return False

    if "GPSLongitude" not in exif_data:
        return False

    return True


def has_camera_info(exif_data):
    if "Make" not in exif_data:
        return False

    if "Model" not in exif_data:
        return False

    return True


def print_verbose(message: str, required_verbosity: int, verbosity: int):
    if verbosity >= required_verbosity:
        print(f"v{required_verbosity}: {message}")


def organize_media(
    source: Path,
    destination: Path,
    recursive: bool,
    with_exif_date: bool,
    gps_only: bool,
    camera_only: bool,
    apply_changes: bool,
    verbosity: int,
):
    if not source.is_dir():
        print_verbose(f"{source} is not a directory.", 1, verbosity)
        return

    if source == destination:
        print_verbose("Source and destination are the same.", 3, verbosity)
        return

    for f in source.iterdir():
        # Recurse into directories
        if f.is_dir() and recursive is True:
            organize_media(
                source=f,
                destination=destination,
                recursive=recursive,
                with_exif_date=with_exif_date,
                gps_only=gps_only,
                camera_only=camera_only,
                apply_changes=apply_changes,
                verbosity=verbosity,
            )

        if not f.is_file():
            print_verbose(f"{f.name} is not a file.", 3, verbosity)
            continue

        # Skip files that are not images or videos
        mime_type, _ = mimetypes.guess_type(f)
        if mime_type is None:
            print_verbose(f"Could not determine the mime type of {f}.", 3, verbosity)
            continue

        if not mime_type.startswith("image") and not mime_type.startswith("video"):
            print_verbose(f"{f} is not an image or video.", 3, verbosity)
            continue

        if mime_type.startswith("video"):
            exif_data = get_exif_data_for_video(f)
        else:
            exif_data = get_exif_data_for_image(f)
        
        requires_exif = with_exif_date or gps_only or camera_only

        if requires_exif is True and exif_data is None:
            print_verbose(f"{f.name} does not have exif data.", 2, verbosity)
            continue

        dates = []

        if exif_data is not None:
            if gps_only is True and not has_gps_info(exif_data):
                print_verbose(f"{f.name} does not have GPS info.", 2, verbosity)
                continue

            if camera_only is True and not has_camera_info(exif_data):
                print_verbose(f"{f.name} does not have make and model.", 2, verbosity)
                continue

            for tag in (
                "CreateDate",
                "MediaCreateDate",
                "DateTimeOriginal",
                "DateTimeDigitized",
                "DateTime",
            ):
                if tag not in exif_data:
                    continue

                dates.append(datetime.strptime(exif_data[tag], "%Y:%m:%d %H:%M:%S"))

        if with_exif_date is True and not dates:
            print_verbose(f"{f.name} does not have an exif date.", 2, verbosity)
            continue

        # Get the file times
        stat = f.stat()
        atime = datetime.fromtimestamp(stat.st_atime)
        ctime = datetime.fromtimestamp(stat.st_ctime)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        dates.extend([atime, ctime, mtime])

        # Get the minimum time
        min_date = min(dates)

        # Create the new file name
        date_string = min_date.isoformat("_", "seconds").replace(":", "-")
        old_name = f.stem.translate(TRANS_TABLE).lower()
        suffix = f.suffix.lower()
        new_name = f"{date_string}__{old_name}{suffix}"

        out_file = destination / str(min_date.year) / new_name
        if apply_changes is True and not out_file.parent.exists():
            out_file.parent.mkdir(exist_ok=True)

        if out_file.exists():
            print_verbose(f"{out_file} already exists.", 2, verbosity)
            continue

        print_verbose(f"Moving {f.name} to {out_file.name}.", 1, verbosity)

        if apply_changes is True:
            out_file.write_bytes(f.read_bytes())
            f.unlink()


if __name__ == "__main__":
    parser = ArgumentParser()

    # Add arguments
    parser.add_argument("--src", type=Path, default=Path.cwd())
    parser.add_argument("--dest", type=Path, default=Path("organized_media"))
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-d", "--with-exif-date", action="store_true")
    parser.add_argument("-g", "--gps-only", action="store_true")
    parser.add_argument("-c", "--camera-only", action="store_true")
    parser.add_argument("-a", "--apply", action="store_true")
    parser.add_argument("-v", "--verbose", action="count", default=0)

    ns = parser.parse_args()

    if ns.apply is True:
        # Create the destination directory if it doesn't exist
        ns.dest.mkdir(exist_ok=True)

    organize_media(
        source=ns.src,
        destination=ns.dest,
        recursive=ns.recursive,
        with_exif_date=ns.with_exif_date,
        gps_only=ns.gps_only,
        camera_only=ns.camera_only,
        apply_changes=ns.apply,
        verbosity=ns.verbose,
    )
