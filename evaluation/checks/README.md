# Reference-free checks

An account book carries a quality signal that needs no ground truth. The item amounts of a block have to add up to the amount on its Summa line, and a run whose arithmetic goes through has read those amounts consistently. `check_amounts.py` makes that signal explicit for the Raitbuch runs of the two pilots.

The check works as a filter. A block that adds up can still hold a misread name, and a mismatch can come from the parser as easily as from the model. What the check produces is a ranked reason to open a facsimile.

## What it does

1. **Parsing.** The amount notation of the Early New High German account book is read as lowercase Roman numerals with `j` as the final-`i` variant, with the hundred and thousand multiplier marks and with the denominations gulden, ducat, mark, pound, schilling, pfennig and heller. Three letters are ambiguous and are resolved by their position in the amount, which is the one place where the parser makes an assumption; the module docstring states each rule with the forms that motivate it.
2. **Block detection.** A block is the run of amount-bearing lines up to the next Summa head, together with the value of that head. A rubric or a foliation line closes the running block, because it opens a new account section.
3. **Verdict per block, per denomination, without any assumed conversion.** `exact-match` means the denominations on both sides are the same set and every one of them adds up. `mismatch` means the same set with at least one denomination off, and both totals are reported. `unverifiable` names its reason, an unparsed token, a missing Summa value, a single item, or differing denominations that an unknown conversion could explain. A mismatching block additionally reports `subset_exact` where exactly one proper subset of the items adds up, which is the signature of a descriptive line carrying an amount that is not an addend.

The parser never guesses. German number words, the ellipsis a run writes where it lost content, misread unit letters and the weight units of the silver accounts are reported as unparsed tokens and turned into no value, and the block that contains one stays undecided. The list of unparsed tokens in the report is therefore also the list of the parser's open edges.

## Ground truth

There is none, and the check needs none. It compares a transcription against itself.

The two cases that anchor the method were verified at the image in the pilot 2 referee review (`../pilot2/review/raitbuch.md`), 300+700+694=1694 on p025 verso and 1220+67=1287 on p030 recto. In both, the arithmetic picked the repeat that the image confirms. Two verified cases carry the method far enough to use the probe as a pointer, and they say nothing about the quality of the runs as a whole.

## Running it

```
python check_amounts.py                        # all Raitbuch runs of pilot and pilot2
python check_amounts.py --runs DIR --out DIR   # other run directories, --runs is repeatable
uv run pytest evaluation/checks                # the parser and block tests, from the repo root
```

The check reads the run files already in the repository, makes no network call and needs no API key.

## Report

`amounts_report.json` and `amounts_report.md` are written next to the script and are regenerated on every run. The Markdown report is German, like the other evaluation reports. It carries the per-cohort counts, the reach of the check, the reasons a block did not decide, the pages on which exactly one repeat adds up, the pages on which every repeat fails, the unparsed tokens with their frequency and the individual decided blocks with both totals.

Reach is reported per cohort with both numerator and denominator, decided blocks against all blocks, pages carrying any signal against all pages, and the runs that write amounts which no Summa line closes. A verdict distribution alone does not say how much material the check reaches, and two decided blocks out of three read like two out of two hundred without the denominator.

The section on pages where exactly one repeat adds up is the operative one. Those pages are the sighting candidates, the places where a targeted reading at the image decides between two machine transcriptions at low cost. It is split by what the counterpart says, because a repeat that contradicts the clean one is a disagreement about the page, while a repeat that decides nothing leaves the clean run unopposed.

License as for the repository: code MIT, documents and data CC BY 4.0.
