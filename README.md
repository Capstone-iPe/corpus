# iPe retrieval corpus

Policy and supporting documents the onboarding copilot retrieves for citation and explanation. ONB still decides fields, files, and the verdict.

**500 documents** under `documents/` (Track B range 500–2,000).

| Folder | What |
|---|---|
| `documents/policy/` | ONB-POL-001–005 |
| `documents/annex/` | Evidence, volume, type aliases |
| `documents/circulars/` | Activation and untrusted text |
| `documents/briefings/` | Background statutes (not extra pack items) |
| `documents/opinions/` | IRAC memos |
| `documents/faq/` | Merchant-facing answers |
| `documents/territorial/` | Non-exceptions |
| `documents/handbook/` | Reviewer handbook |
| `documents/not-in-force/` | Rejected drafts — discard if retrieved |

`corpus-build/` regenerates the bulk IRAC memos. The indexer in `copilot-svc` only reads `documents/**/*.md`.

This repo is a **git submodule** in `Capstone-iPe/copilot-svc` (path `corpus`). Analysis links here; it does not vendor the pack.
