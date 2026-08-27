# Scholarly review of the pilot-2 inventory transcriptions

Six pages of the pilot-2 inventory cohort (it02, gemini-3.7-flash, two repeats each) were compared line by line against the page images. Three pages come from Sigmundskron A 225.1 (1487) and were chosen as the lowest word-consistency substantive pages of that document, two from Pergine A 273.5 (1446) as high-consistency controls, and one is the opening page of Schoeneck A 185.1 (1492). Images were read from the shared benchmark cache at their native resolution and again at three- to eightfold magnification for individual lines. The Transkribus working transcription was consulted as a second opinion; it is not ground truth and is shown below to be wrong in at least one place where both machine repeats are right.

## Coverage

Coverage is not the problem. On all six pages the number of written lines counted on the image matches the number of lines emitted by both repeats exactly: 17 for Sigmundskron fol. 4v (1225x3465), 17 for fol. 3r (1193x3465), 15 for fol. 3v (1256x3568, sent downscaled to 1232x3500), 34 for Pergine fol. 3r (1104x3327), 34 for Pergine fol. 2r (1140x3283) and 23 for Schoeneck fol. 1r (1721x1285). No line is skipped and none is invented.

The `ref_lines` deficits recorded in the summary are artefacts of the reference, not omissions. The working transcription prefixes a `[fol.Nr]` marker line that the model correctly does not hallucinate, and on Pergine fol. 3r it splits `nicht vast gut` and `Suma der pet xxvj` into two units although the image carries them on one written line, where both repeats follow the image. On Schoeneck fol. 1r the machine output is more complete than the reference: both repeats capture the pencil date, the oval archival stamp and the vertical shelfmark in the left margin, which the working transcription omits, though they disagree on the shelfmark reading (`Ums.` against `Hss.`). The one paratextual element silently dropped is the `K. K. STATTHALTEREI-ARCHIV` stamp at the foot of Sigmundskron fol. 3r.

## Numbers and quantities

Numbers fail in a way that the current metrics cannot see. On Sigmundskron fol. 3v the image reads `Vier eysen kellen` (line 3) and `Vier hafen deckhen` (line 6); both repeats read `drei` in both places. On fol. 4v line 7 the image reads `Drew eysnen gatter` and both repeats read `Zwen`. That is three lines on two folios where the scribe's `Vier`/`Drew` glyph with its long approach stroke is systematically downgraded, identically in both runs. Because the repeats agree, `consistency_numbers` reports 1.0 for exactly these pages. Self-consistency between repeats is therefore not a quality signal for numerals; it measures only whether the model is stable in its errors.

The single largest distortion is Sigmundskron fol. 3r line 15. The image reads `Sechsunddreissig hueltzen taler new`; r1 gives `Sechshundertt`, r2 `Sechshundertacht`. A count of 36 becomes 600 or 608. The composed cardinal is decomposed into a hundreds form while the simple cardinals on the same page (`Sechtzehen`, `funff`) are read correctly.

Roman numerals fail by minim count rather than by recognition. On Pergine fol. 3r the summa of beds is written `xxvj` and both repeats read `xxvij`, adding a minim to the running total of the whole inventory. On Schoeneck fol. 1r each repeat corrupts exactly one numeral and never the same one: r1 turns the written `iij tisch` into `ij`, r2 turns the written `xij spanpet` into `iiij`. This is the one case in the cohort where a repeat diff would have flagged the right lines.

Individual repeats also invent quantities outright. Sigmundskron fol. 4v line 5 reads `Ain clainer kessl` and r1 gives `Drei`; line 4 reads `Vier phannen` and r2 gives `Drei`. On fol. 3v line 4 the image reads `Drey phannen` and r2 gives `Acht`, and on line 7 r1 drops the quantity `Drew` entirely and starts the line with `Item` instead.

## Hallucination

Three kinds occur, in ascending order of harm.

Substituted content words. Sigmundskron fol. 3v line 7 reads `Drew messingpeckh vnd ain prochen messingpeckh`; both repeats turn `prochen` (broken) into `grossen`/`grosen`, inverting the condition statement that is the point of an appraisal inventory. On line 9 the image reads `Ain oel stain` and both repeats give `Ain oel pann`; the same object fails again on Schoeneck fol. 1r as `oel trainn`. On Sigmundskron fol. 4v line 9 the image reads `zugehoren` and r1 writes `zugeschriben`.

Invented editorial apparatus. On Pergine fol. 2r line 27 both repeats wrap the rubric in strikethrough markup, `~~bey der ewig~~` and `~~bey der styeg~~`. Magnified, the line reads `bey der Styeg` written plainly, with no deletion stroke anywhere. On line 17 of the same page the human transcriber marked a passage illegible; r1 fills the gap with `v[ast]` in editorial brackets. A bracketed guess is more damaging than an open gap because it carries the form of an editorial decision.

Semantic reversals and lost facts. On Schoeneck fol. 1r line 22 the image reads `ist nit eingefast` and r1 drops the negation, so the gun becomes mounted rather than unmounted. On line 7 of the same page r2 replaces the dating element `Sannd Katrein tag` with `Sannd Lucien tag`, moving the document by nearly a month, and prefixes a `Daz` to the opening protocol that the image does not have. On Pergine fol. 3r line 13 the image reads `In des Cuntzen harnasch` and r1 gives `In des Iungen harnasch`, dissolving a personal name into an adjective; r2 at least keeps a name-shaped token, though the wrong one. On Pergine fol. 2r line 23 r2 turns the name `Leo` into `los`.

## Error classes

Proper names are the weakest token class regardless of hand quality. They fail on the calligraphic Pergine bastarda (`Cuntzen`, `ergker`) as reliably as on the fast Schoeneck cursive (`Gabein Kuenigls` becoming `baben kungls` or `Baben Rungels`). Names are exactly the tokens a reader cannot repair from context, so their failure rate should be reported separately.

Abbreviation strokes are expanded into non-words rather than left open. The suspended `ainer` on Pergine fol. 2r is rendered as `aind` by both repeats at four positions. The nasal bar over final `-en` drives most of the mangled Sigmundskron tokens.

Recurring realia of the genre are unknown to the model. On Sigmundskron fol. 4v the word `eysen` occurs eight times across four lines (`eysnen gatter`, `eysengeschirr`, `purden eysen`, `von eysen`) and is never once read correctly; r1 offers `zynnen`, `tzschmigeschirr`, `tzschin`, r2 offers `zwen`, `hefenn`. On Schoeneck fol. 1r `truhen` recurs seven times and r1 renders it as the non-word `tengen` every time, having locked onto its first guess, while r2 reads `trugen` throughout and is essentially right. `schatzwert` becomes `schutzwert` in both Pergine repeats, and `Schreybtafel` becomes `steyrertafel` in both Schoeneck repeats.

One letterform confusion is repeat-specific rather than model-wide: on Pergine fol. 2r r1 reads long s as f throughout (`palaft` seven times, `palafter`, `haupcmans`) while r2 has none of it. That is the cleanest single-variable difference between two repeats in the cohort.

## Repeat comparison and verdicts

r2 is better on Sigmundskron fol. 4v and fol. 3r, on Pergine fol. 2r and on Schoeneck fol. 1r; r1 is better on Sigmundskron fol. 3v and on Pergine fol. 3r. There is no stable winner, and the pattern is that r2 reads more freely, which helps on hard lexis and hurts on quantities. The differences are stochastic at token level, but every error that matters most is shared by both repeats: the `Vier`/`drei` downgrade, the `Sechsunddreissig`/`Sechshundert` inflation, the `xxvij` minim, the invented strikethrough, `oel stain`, `schatzwert`, `Schreybtafel`. A second repeat catches the noise and is blind to the bias.

| Page | Verdict | Most important correction |
|---|---|---|
| Sigmundskron fol. 4v (p8) | unusable | Object nouns wrong in about two thirds of the lines and quantities unreliable in both directions; only the line segmentation and the entry/rubric structure survive |
| Sigmundskron fol. 3r (p5) | needs-targeted-correction | `Sechsunddreissig` inflated to `Sechshundert(acht)` |
| Sigmundskron fol. 3v (p6) | needs-targeted-correction | Four of six numeral-bearing lines wrong in at least one repeat, two wrong in both |
| Pergine fol. 3r (p7) | usable-as-draft | Summa `xxvj` read as `xxvij`; restore the name `Cuntzen` |
| Pergine fol. 2r (p5) | usable-as-draft | Remove the unwarranted strikethrough and the invented bracket expansion `v[ast]` |
| Schoeneck fol. 1r (p1) | needs-targeted-correction | Restore `Sannd Katrein tag` and the negation in `ist nit eingefast` |

The split runs along the hand, not the document: the calligraphic Pergine bastarda is at correction-pass quality, the two fast Tyrolean cursives are not.

## A caveat on the reference

On Pergine fol. 3r line 29 the image reads `Darnachht die polster vnd kuessen`, which both repeats capture. The Transkribus working transcription has `Vermerkht`. CER against the working transcription therefore penalizes a correct machine reading, and the reported CER figures for this cohort carry an unknown amount of that. The working transcription is a comparison signal, and the summary already says so; the practical consequence is that no page should be accepted or rejected on CER alone.

## Three process lessons

Give numerals their own pass and stop reporting repeat agreement as number quality. Every numeral-bearing token, word-numeral and roman numeral alike, should be re-read in a second stage on a cropped line image with an instruction to count minims explicitly, and any numeral where the two repeats disagree should hard-flag its line for human review. The current `consistency_numbers` field reports 1.0 for the three Sigmundskron pages where both repeats are wrong in the same direction; until that is fixed the field invites false confidence and should be renamed or dropped rather than read as accuracy.

Forbid invented editorial apparatus. The prompt must state that deletion markup is emitted only where a deletion stroke is visible on the page, that no expansion may be placed in brackets unless the abbreviation sign is visible, and that anything unreadable goes into the `uncertain` list or an explicit gap token. Both repeats produced a strikethrough on plainly written text and one produced a bracketed guess for a passage a human marked illegible; these are the errors a later reader is least able to detect, because they look like editorial decisions.

Supply a genre lexicon and diff the repeats at token level. The recurring realia of the Burgeninventar (truhe, eysen, ster, glockspeys, oel stain, messingpeckh, schatzwert, spanpet, ergker, zwilchin ziech) should be given to the model as a controlled word list per document, since the failures cluster on exactly these terms and one repeat locked onto a non-word for seven consecutive occurrences. The reviewer's work list should then be the token-level diff between the two repeats plus every token flagged as uncertain, rather than a single aggregate score per page, which on this evidence tells a corrector nothing about where to look.
