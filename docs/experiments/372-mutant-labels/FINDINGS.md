# Findings — 2026-10-05

**The set meets #372's bar: 231 cases from 52 bugs, 133 killed (58%) and 98
survived (42%).** The bar is at least 200 cases, with at least 30% killed and
at least 30% survived.

**Survivor spot-check: 0 of 20 sampled edits changed no behaviour.** A person
checked 20 edits drawn at random from the 65 edits that survived. For each,
the agent wrote a one-line reading and the human confirmed it. Two of the 20
change only a progress message shown on screen, and the human ruled that a
message change counts as a behaviour change. The sample is small: 0 of 20 is
consistent with an equivalent-edit rate of up to about 14% (one-sided 95%).

| project | cases | killed | survived |
|---|---|---|---|
| youtube-dl | 136 | 88 | 48 |
| thefuck | 56 | 39 | 17 |
| tqdm | 35 | 4 | 31 |
| PySnooper | 4 | 2 | 2 |

What the numbers do not show:

- **Constant changes dominate.** 140 of the 231 cases come from changing a
  constant, mostly blanking a string. Fewer than 10 come from swapping `+`/`-`,
  swapping `and`/`or`, or dropping a `not`. A judge scored on this set is
  mostly being scored on constant edits.
- **tqdm is mostly survivors** (31 of 35). Its chosen tests format numbers and
  times, and rarely reach the edited branches.
- **35 of the 87 pinned bugs produced no case.** 15 had no test pytest would
  collect. 10 had no line an operator applies to. 10 lost every chosen test to
  the control run, through the two version clashes in the README's Traps.

The raw counts are in `findings.json`.
