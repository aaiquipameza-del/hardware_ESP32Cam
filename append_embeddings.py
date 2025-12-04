#!/usr/bin/env python3
import sys
import json
import os
from pathlib import Path
import numpy as np

ENCODINGS_NPY = "encodings.npy"
LABELS_JSON = "labels.json"


def load_master():
    if Path(ENCODINGS_NPY).exists():
        enc_master = np.load(ENCODINGS_NPY)
        if enc_master.ndim == 1:
            enc_master = enc_master.reshape(1, -1)
        if Path(LABELS_JSON).exists():
            labels = json.loads(Path(LABELS_JSON).read_text(encoding="utf-8"))
        else:
            labels = []
    else:
        enc_master = np.zeros((0, 128), dtype=np.float32)
        labels = []
    return enc_master, labels


def append_embeddings(name, enc_list):
    enc_master, labels = load_master()
    # normalize enc_list to numpy
    enc_new = np.vstack([np.asarray(e, dtype=np.float32).reshape(1, -1) for e in enc_list])
    if enc_master.size:
        enc_all = np.vstack([enc_master, enc_new])
    else:
        enc_all = enc_new
    labels += [name] * len(enc_list)
    np.save(ENCODINGS_NPY, enc_all)
    Path(LABELS_JSON).write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
    return enc_all.shape[0], len(labels)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({"ok": False, "message": f"Invalid JSON on stdin: {e}"}))
        sys.exit(2)

    name = payload.get("name")
    encs = payload.get("encodings")
    if not name or not encs or not isinstance(encs, list):
        print(json.dumps({"ok": False, "message": "Missing name or encodings in input"}))
        sys.exit(3)

    try:
        total_rows, total_labels = append_embeddings(name, encs)
        print(json.dumps({"ok": True, "message": "Appended embeddings", "total_rows": total_rows}))
        sys.exit(0)
    except Exception as e:
        print(json.dumps({"ok": False, "message": f"Exception: {e}"}))
        sys.exit(4)


if __name__ == '__main__':
    main()
