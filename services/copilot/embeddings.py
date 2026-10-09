"""Local embedding leg (multilingual-e5-small, int8 ONNX).

Deliberately NOT bge-m3 as the brief suggests: bge-m3 is 568M (~2.3 GB) with no
int8 ONNX export, and this machine has ~1 GB free RAM. multilingual-e5-small
int8 is 113 MB and is genuinely cross-lingual, which is what a Taglish query
against an English legal corpus actually needs.

e5 models require asymmetric prefixes:
    query  -> "query: ..."
    passage-> "passage: ..."
Skipping them measurably degrades retrieval quality.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ASSET_DIR = REPO_ROOT / "models" / "weights" / "multilingual-e5-small-int8"
# The downloader flattens "onnx/<name>" to "<name>", and mirrors publish several
# quantisation targets. Accept whichever int8/quantised graph is actually present.
_CANDIDATES = [
    # Flattened form written by models/download_models.py ("onnx/<name>" -> "<name>")
    # with "/" replaced by "__".
    _ASSET_DIR / "onnx__model_qint8_avx512_vnni.onnx",
    _ASSET_DIR / "onnx" / "model_qint8_avx512_vnni.onnx",
    _ASSET_DIR / "model_qint8_avx512_vnni.onnx",
    _ASSET_DIR / "onnx" / "model_quantized.onnx",
    _ASSET_DIR / "model_quantized.onnx",
    _ASSET_DIR / "onnx__model_quantized.onnx",
    _ASSET_DIR / "onnx" / "model.onnx",
    _ASSET_DIR / "model.onnx",
]
ONNX_PATH = next((p for p in _CANDIDATES if p.exists()), _CANDIDATES[0])
TOKENIZER_DIR = _ASSET_DIR

MAX_LEN = 512

# CLS is what multilingual-e5 requires for retrieval. Overridable only so the
# ablation can reproduce the old behaviour deliberately, never by accident.
POOLING = "cls"


def pool(vecs, mask, mode: str = "cls"):
    """Reduce token vectors to one L2-normalised sentence vector.

    `intfloat/multilingual-e5-small` requires **CLS pooling** - the first token
    embedding - for retrieval, per its model card. Mean pooling is the BERT
    convention and silently produces vectors in the wrong space: the ablation in
    `eval/retrieval_ablation.py` measured the dense leg scoring *below* a
    lexical-only baseline while mean pooling was in use.

    `mode` exists so the regression cannot be reintroduced silently: an
    unrecognised value raises rather than defaulting to something plausible.
    """
    import numpy as np

    if mode == "cls":
        pooled = np.asarray(vecs)[:, 0, :]
    elif mode == "mean":
        m = np.asarray(mask)[..., None].astype("float32")
        pooled = (np.asarray(vecs) * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
    else:
        raise ValueError(f"unknown pooling mode: {mode!r} (expected 'cls' or 'mean')")

    norms = np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-9, None)
    return (pooled / norms).astype("float32")


class Embedder:
    """Lazy ONNX embedder. Never raises at import time - the copilot degrades to
    BM25-only if this fails, so availability is a property, not an exception."""

    def __init__(self) -> None:
        self._session = None
        self._tokenizer = None
        self.available = False
        self.reason = "not loaded"

        if not ONNX_PATH.exists():
            self.reason = f"model not downloaded ({ONNX_PATH.name})"
            return

        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(
                str(ONNX_PATH), sess_options=opts, providers=["CPUExecutionProvider"]
            )
            self._tokenizer = AutoTokenizer.from_pretrained(str(TOKENIZER_DIR))
            self.available = True
            self.reason = "ready"
        except Exception as exc:  # noqa: BLE001
            self.reason = f"{type(exc).__name__}: {exc}"
            self.available = False

    def _run(self, texts: list[str], prefix: str) -> list:
        import numpy as np

        inputs = self._tokenizer(
            [prefix + t for t in texts],
            padding=True,
            truncation=True,
            max_length=MAX_LEN,
            return_tensors="np",
        )
        feed = {k: v for k, v in inputs.items()}

        # The exported XLM-R graph requires token_type_ids; BERT tokenizers omit it.
        required = {i.name for i in self._session.get_inputs()}
        if "token_type_ids" in required and "token_type_ids" not in feed:
            feed["token_type_ids"] = np.zeros_like(feed["input_ids"], dtype=np.int64)
        # Drop anything the graph does not accept (e.g. token_type_ids on XLM-R exports).
        feed = {k: v for k, v in feed.items() if k in required}

        outputs = self._session.run(None, feed)
        # e5 requires CLS pooling, not the BERT-style mean. See `pool()`.
        return pool(outputs[0], inputs["attention_mask"], mode=POOLING)

    def encode_queries(self, texts: list[str]):
        return self._run(texts, "query: ")

    def encode_passages(self, texts: list[str]):
        return self._run(texts, "passage: ")

    def encode_chunks(self, texts: list[str], batch_size: int = 16):
        import numpy as np

        out = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            out.append(self.encode_passages(batch))
            print(f"      embedded {min(i + batch_size, len(texts))}/{len(texts)}", flush=True)
        return np.vstack(out)