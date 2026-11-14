# Corpus generators

Scripts that expand IRAC memos into `../corpus/`.

```bash
python3 corpus-build/expand.py
python3 corpus-build/stats.py
```

Does not overwrite handwritten POL / ANX / CIR / SOP / FAQ-001. Commit and push, rebuild the search index (`PYTHONPATH=src python -m index build`), then restart the API.
