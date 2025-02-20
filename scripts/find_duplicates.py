from argparse import ArgumentParser
import mimetypes
from pathlib import Path
from typing import Callable, NamedTuple

import imagehash
from PIL import Image


HASH_FUNCS: dict[str, imagehash.ImageHash] = {
    "phash": imagehash.phash,
    "ahash": imagehash.average_hash,
    "dhash": imagehash.dhash,
    "whash": imagehash.whash,
    "colorhash": imagehash.colorhash,
}

class HashResult(NamedTuple):
    hash: imagehash.ImageHash
    file: Path


def get_hashes(
    source: Path,
    recursive: bool,
    hash_func: Callable[[Image.Image], imagehash.ImageHash],
) -> list[HashResult]:
    hashes: list[HashResult] = []

    if not source.is_dir():
        return hashes

    for f in source.iterdir():
        if recursive is True and f.is_dir():
            hashes.extend(get_hashes(
                source=f,
                recursive=recursive,
                hash_func=hash_func,
            ))

        if not f.is_file():
            continue

        mimetype, _ = mimetypes.guess_type(f)
        if not mimetype or not mimetype.startswith("image"):
            continue

        with Image.open(f) as img:
            try:
                img_hash = hash_func(img)
            except Exception as e:
                print(f"Error processing {f}: {e}")
                continue

            hashes.append(HashResult(hash=img_hash, file=f))

    return hashes


def get_duplicates(hashes: list[HashResult]):
    print("sorting hashes...")
    hashes.sort(key=lambda x: str(x.hash))
    stack = []
    duplicates = set()

    print("finding duplicates...")
    for result in hashes:
        if not stack:
            stack.append(result)
            continue

        distance = stack[-1].hash - result.hash
        if distance < ns.hamming_distance:
            stack.append(result)
        else:
            if len(stack) > 1:
                print(f"found duplicates: {len(stack)}")
                duplicates.add(frozenset(item.file for item in stack))
            stack.clear()
            stack.append(result)

    # check for duplicates at the end of the list
    if len(stack) > 1:
        print(f"found duplicates: {len(stack)}")
        duplicates.add(frozenset(item.file for item in stack))

    return duplicates


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--src", type=Path, default=Path.cwd())
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-H", "--hash", type=str, choices=HASH_FUNCS, default="phash")
    parser.add_argument("-d", "--hamming-distance", type=int, default=0)

    ns = parser.parse_args()

    print("getting hashes...")
    hashes = get_hashes(
        source=ns.src,
        recursive=ns.recursive,
        hash_func=HASH_FUNCS[ns.hash],
    )

    from pympler import asizeof
    print(f"size of hashes: {asizeof.asizeof(hashes)}")

    duplicates = get_duplicates(hashes)

    for d in duplicates:
        print("\n".join(f.name for f in d))
        print()
