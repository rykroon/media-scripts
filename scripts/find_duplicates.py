from argparse import ArgumentParser
from dataclasses import dataclass
import mimetypes
from pathlib import Path
from typing import Callable, NamedTuple
import time

import imagehash as ih
from PIL import Image


HASH_FUNCS: dict[str, ih.ImageHash] = {
    "phash": ih.phash,
    "ahash": ih.average_hash,
    "dhash": ih.dhash,
    "whash": ih.whash,
}

@dataclass(slots=True)
class HashResult:
    hash_str: str
    file_name: str

    def __sub__(self, other: "HashResult") -> int:
        return ih.hex_to_hash(self.hash_str) - ih.hex_to_hash(other.hash_str)


def get_hashes(
    source: Path,
    recursive: bool,
    hash_func: Callable[[Image.Image], ih.ImageHash],
) -> list[HashResult]:
    hash_results: list[HashResult] = []

    if not source.is_dir():
        return hashes

    for f in source.iterdir():
        if recursive is True and f.is_dir():
            hash_results.extend(get_hashes(
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

            hash_results.append(HashResult(hash_str=str(img_hash), file_name=f.name))

    return hash_results


def get_duplicates(
    hash_results: list[HashResult], hamming_distance: int = 0
) -> set[frozenset[Path]]:
    print("sorting hashes...")
    hash_results.sort(key=lambda x: x.hash_str)
    stack: list[HashResult] = []
    duplicates: set[frozenset[str]] = set()

    print("finding duplicates...")
    for result in hash_results:
        if not stack:
            stack.append(result)
            continue

        if stack[-1] - result < hamming_distance:
            stack.append(result)
        else:
            if len(stack) > 1:
                print(f"found duplicates: {len(stack)}")
                duplicates.add(frozenset(item.file_name for item in stack))
            stack.clear()
            stack.append(result)

    # check for duplicates at the end of the list
    if len(stack) > 1:
        print(f"found duplicates: {len(stack)}")
        duplicates.add(frozenset(item.file_name for item in stack))

    return duplicates


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--src", type=Path, default=Path.cwd())
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-H", "--hash", type=str, choices=HASH_FUNCS, default="phash")
    parser.add_argument("-d", "--hamming-distance", type=int, default=0)

    ns = parser.parse_args()

    start = time.time()

    print("getting hashes...")
    hashes = get_hashes(
        source=ns.src,
        recursive=ns.recursive,
        hash_func=HASH_FUNCS[ns.hash],
    )

    from pympler import asizeof
    print(f"size of hashes: {asizeof.asizeof(hashes)}")

    duplicates = get_duplicates(hashes, ns.hamming_distance)

    end = time.time()
    print(f"""Ran in {end - start:.2f} seconds""")

    for d in duplicates:
        print("\n".join(f for f in d))
        print()
    
