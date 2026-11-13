# Corpus generators

Scripts that expand IRAC memos into `../documents/`.

```bash
python3 corpus-build/expand.py
python3 corpus-build/stats.py
```

Does not overwrite handwritten POL / ANX / CIR / SOP / FAQ-001. Commit and push this repo, then bump the submodule pointer in `copilot-svc` and rebuild the index (see the repo root README).
