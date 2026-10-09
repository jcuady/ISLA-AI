"""Pooling for the local embedding model.

`intfloat/multilingual-e5-small` is an XLM-RoBERTa encoder whose model card is
explicit about retrieval: *"please use the CLS pooling, i.e. the first token
embedding"*, with `query: ` / `passage: ` prefixes and a cosine similarity.

We were mean-pooling. The dense vectors were therefore in the wrong space, which
is measurable: the ablation in `eval/retrieval_ablation.py` showed the dense leg
scoring *below* the lexical-only baseline, i.e. it was actively hurting retrieval.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.copilot.embeddings import pool  # noqa: E402


def vecs_and_mask() -> tuple:
    # two sequences, two tokens: [CLS] a   and   [CLS] b c
    vecs = np.array(
        [
            [[1.0, 0.0], [0.0, 1.0], [9.0, 9.0]],  # third slot is padding
            [[0.0, 2.0], [4.0, 0.0], [8.0, 8.0]],
        ],
        dtype="float32",
    )
    mask = np.array([[1, 1, 0], [1, 1, 1]], dtype="float32")
    return vecs, mask


def test_cls_pooling_takes_the_first_token():
    vecs, mask = vecs_and_mask()
    out = pool(vecs, mask, mode="cls")
    assert np.allclose(out[0], np.array([1.0, 0.0]) / np.linalg.norm([1.0, 0.0]))
    assert np.allclose(out[1], np.array([0.0, 2.0]) / np.linalg.norm([0.0, 2.0]))


def test_cls_pooling_ignores_padding_entirely():
    vecs, mask = vecs_and_mask()
    padded = vecs.copy()
    padded[0, 2] = [999.0, 999.0]
    assert np.allclose(pool(padded, mask, "cls"), pool(vecs, mask, "cls"))


def test_mean_pooling_averages_the_unmasked_tokens():
    vecs, mask = vecs_and_mask()
    out = pool(vecs, mask, mode="mean")
    expected0 = np.array([0.5, 0.5])
    assert np.allclose(out[0], expected0 / np.linalg.norm(expected0))


def test_both_modes_return_unit_vectors():
    vecs, mask = vecs_and_mask()
    for mode in ("cls", "mean"):
        norms = np.linalg.norm(pool(vecs, mask, mode), axis=1)
        assert np.allclose(norms, 1.0), mode


def test_default_mode_is_cls_because_that_is_what_the_model_requires():
    vecs, mask = vecs_and_mask()
    assert np.allclose(pool(vecs, mask), pool(vecs, mask, "cls"))


def test_an_unknown_mode_is_rejected_rather_than_silently_mean_pooling():
    vecs, mask = vecs_and_mask()
    with pytest.raises(ValueError):
        pool(vecs, mask, mode="average")


def test_pooling_output_is_float32_for_onnxruntime():
    vecs, mask = vecs_and_mask()
    assert pool(vecs, mask).dtype == np.float32