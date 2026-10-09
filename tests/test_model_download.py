"""Resumable model downloads.

The original downloader preallocated the target file and re-fetched every block,
so a transfer that stalled at 97% after two hours started again from zero. This
covers the seam that decides which byte ranges are actually still missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.download_models import block_ranges, missing_ranges, write_block  # noqa: E402


def test_block_ranges_covers_the_whole_file(tmp_path: Path):
    f = tmp_path / "blob"
    f.write_bytes(b"\x00" * 10)
    assert block_ranges(10, 4) == [(0, 3), (4, 7), (8, 9)]


def test_block_ranges_on_an_exact_multiple_has_no_empty_tail(tmp_path: Path):
    assert block_ranges(8, 4) == [(0, 3), (4, 7)]


def test_missing_ranges_on_a_preallocated_file_is_everything(tmp_path: Path):
    f = tmp_path / "blob"
    f.write_bytes(b"\x00" * 16)
    assert missing_ranges(f, 16, 4) == [(0, 3), (4, 7), (8, 11), (12, 15)]


def test_missing_ranges_skips_a_block_that_already_has_data(tmp_path: Path):
    f = tmp_path / "blob"
    data = bytearray(b"\x00" * 16)
    data[4:8] = b"done"
    f.write_bytes(bytes(data))
    assert missing_ranges(f, 16, 4) == [(0, 3), (8, 11), (12, 15)]


def test_missing_ranges_on_a_complete_file_is_empty(tmp_path: Path):
    f = tmp_path / "blob"
    f.write_bytes(b"0123456789abcdef")
    assert missing_ranges(f, 16, 4) == []


def test_missing_ranges_tolerates_a_short_file(tmp_path: Path):
    """A truncated file must be treated as fully missing, never as an IndexError."""
    f = tmp_path / "blob"
    f.write_bytes(b"abc")
    assert missing_ranges(f, 16, 4) == [(0, 3), (4, 7), (8, 11), (12, 15)]


def test_missing_ranges_on_a_missing_file_is_everything(tmp_path: Path):
    assert missing_ranges(tmp_path / "nope", 8, 4) == [(0, 3), (4, 7)]


def test_write_block_writes_at_the_right_offset(tmp_path: Path):
    f = tmp_path / "blob"
    f.write_bytes(b"\x00" * 12)
    write_block(f, 4, b"ABCD")
    assert f.read_bytes() == b"\x00\x00\x00\x00ABCD" + b"\x00" * 4


def test_write_block_returns_the_number_of_bytes_written(tmp_path: Path):
    f = tmp_path / "blob"
    f.write_bytes(b"\x00" * 8)
    assert write_block(f, 0, b"1234") == 4