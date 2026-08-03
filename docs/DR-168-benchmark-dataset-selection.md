# DR-168 — Benchmark dataset selection (resolves M-B1)

*Decision Record. Status: **accepted**. Raised by #168 (retiring the Stage-1 plan); content moved verbatim from `Stage-1-Development-Plan.md` §10, which resolved the §11.2 decision the spec deferred. Referenced from #37 (M-B1).*

This resolves the §3.2 decision the spec flagged in §11.2 ("exact dataset selection, subset sizing, and licenses are confirmed in the development plan before adoption"). Two datasets cover all five benchmark layers; each is chosen because its native structure already matches the tuples the reviewer needs.

## 1. Primary: SWE-bench Verified

**What it is.** A 500-instance, human-validated subset of the SWE-bench test set — real GitHub issue → gold pull-request patch → the PR's own test changes — drawn from 12 popular Python repositories (astropy, django, sympy, matplotlib, flask, requests, scikit-learn, and similar). Validated by professional annotators as genuinely solvable, which strips out the mislabeled/underspecified instances that add noise to accuracy figures.

**Why it fits this product almost exactly.** Each instance already carries the fields the checker consumes and the ground truth the benchmark scores against:

| SWE-bench field | Role in our benchmark |
|---|---|
| `problem_statement` (issue title + body) | Task input → obligation decomposition (M1) |
| `patch` (gold PR patch, test code removed) | Gold implementation for coverage/agent-output labels (M-B4) |
| `test_patch` (tests the PR added) | The test evidence the semantic analyzer judges (M5) |
| `FAIL_TO_PASS` (tests tied to the fix) | Ground-truth "the behavior the change must demonstrate" — gap labels |
| `PASS_TO_PASS` (tests green before and after) | Ground-truth regression/compatibility set — feeds mutant labels (M-B3) |
| `difficulty` (Verified only) | Stratification variable for subset sampling |

The `FAIL_TO_PASS` / `PASS_TO_PASS` split is the single most valuable feature: it is a ready-made, human-checked partition of "tests that evidence the requested behavior" vs. "tests that guard existing behavior" — precisely the distinction §9.2/§9.3 ask the reviewer to make.

**Sizing.** Start with a **stratified ~100-instance subset** across the `difficulty` field for fast iteration during M1–M7; scale to the full 500 for the M9.4 headline figures. Full SWE-bench (2,294) and SWE-bench Lite (300) are available if more volume is wanted, but Verified's human validation makes it the better accuracy base. **Excluded:** SWE-bench Multimodal (100 visual/UI instances — out of scope per §4) and SWE-bench Multilingual (non-Python — out of Stage-1 scope §13.2).

## 2. Secondary: BugsInPy

**What it is.** ~500 hand-curated, reproducible real bugs from 17 Python projects (pandas, keras, matplotlib, scrapy, ansible, youtube-dl, and others), each isolated with a buggy version, a fixed version, and the relevant failing test. Its CLI ships `checkout`, `compile`, `test`, `coverage`, and **`mutation`** commands over a Docker image.

**Why it earns a place alongside SWE-bench.** It is the natural backbone for the **offline-mutant test-strength layer (M-B3)**: a per-bug reproducible checkout plus a built-in mutation and coverage harness is exactly the "inject a mutant into real code with a real passing test; if it survives, that's a ground-truth weak-evidence label" recipe (§11.2, §8.2) — without our having to build a mutation runner just to *generate labels*. It also doubles as ready-made fixtures for exercising the M8 execution tier against genuinely hermetic Python suites.

## 3. Layer-to-dataset mapping (§11.2)

| §11.2 layer | Dataset | Notes |
|---|---|---|
| Ready-made labeled instances (base) | **SWE-bench Verified** | Human-validated; FAIL_TO_PASS/PASS_TO_PASS as gap/regression labels. |
| Real merged PRs + follow-up-fix labels | Mined from SWE-bench's 12 configured repos | Reuse existing per-repo environment setup (M-B2). |
| Offline mutants for test-strength labels | **BugsInPy** (primary), SWE-bench PASS_TO_PASS (secondary) | BugsInPy's `mutation`/`coverage` commands generate labels directly (M-B3). |
| Real agent output (on-thesis) | Agents run on **SWE-bench Verified** | Label vs. gold `patch` + `FAIL_TO_PASS` (M-B4). |
| Hand-curated archetypes | Built in-house (M-B5a) | Interpretability only; never the basis for accuracy claims (§11.2). |

## 4. Licensing posture

- **SWE-bench harness/code** — MIT. Safe to build tooling on and to vendor.
- **SWE-bench dataset instances** — no single dataset-wide license; **each instance carries the license of its source repo at that commit**, and the included repos permit at least non-commercial use (most of the 12 — astropy, django, sympy, flask, requests, scikit-learn — are permissive BSD/Apache/PSF). Using the data to *measure* the reviewer internally is standard, low-risk research use. **Redistributing** a derived dataset, or shipping any repo's code inside the commercial product, requires a per-repo license check first — the ingester therefore records each instance's repo license as a field (M-B1 acceptance).
- **BugsInPy** — the repository **declares no license file**, which defaults to "all rights reserved." Academic/internal benchmarking use is the norm and low-risk, but treat it as **confirm-before-redistribution**: do not bundle BugsInPy content into the product or a public derived dataset without contacting the authors (soarsmu). Because BugsInPy is used only to *generate labels offline* (not shipped), this constraint does not block Stage 1.

**Net for the commercial goal:** neither dataset needs to ship inside the product. Both are used behind the scenes to validate accuracy, so the licensing constraints bear on *publishing a derived benchmark*, not on selling the reviewer. The one hard gate is recording per-instance repo licenses (SWE-bench) and not redistributing BugsInPy content (M-B1 / M-B3 acceptance checks).

## 5. Residual actions (kept in M-B1)

1. Confirm the exact SWE-bench Verified snapshot/version pin and record it for reproducibility.
2. Record each ingested instance's source-repo license as a case field; flag any copyleft repo for the redistribution decision.
3. Confirm BugsInPy's usage terms with the authors before any derived-dataset release; internal label generation may proceed meanwhile.

---

## Why this is a DR and not an issue body

The selection itself is settled, but the reasoning behind it is reference material — it is what you re-read when the licensing question resurfaces, when a reviewer asks why not SWE-bench Lite, or when Stage 2 wants a sixth layer. Issue bodies are for work with a lifecycle; this has none left. The three residual actions in §5 above *do* have a lifecycle and stay tracked on #37.
