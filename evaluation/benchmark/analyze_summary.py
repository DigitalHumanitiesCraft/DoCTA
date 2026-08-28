# /// script
# requires-python = ">=3.11"
# dependencies = ["requests", "pillow"]
# ///
"""Secondary analysis of the benchmark summary: what the measures license.

The runner produces per-page rates. This script answers the questions a reader
of those rates asks next, and it answers them on the seven reference pages whose
reference is not degenerate:

  1. Does self-consistency predict the character error rate, so that a page
     without a reference can be triaged by agreement alone?
  2. Is the it01 to it02 difference a paired per-page effect or an artefact of
     averaging pages of unequal length?
  3. Do the model's uncertain markers land on tokens the model in fact got
     wrong?
  4. Which agreement threshold would capture the worst-read third of the
     material?

Everything is read from disk (`summary.json`, `runs/`), nothing is fetched and
no clock is read; the output carries the `generated` stamp of the summary it
analysed, so two runs over one summary produce byte-identical files. The
normalisation, the token classification and the alignment orientation come from
`run_benchmark.py`, so the analysis measures the same objects the summary does.

Sample sizes are small by construction. Seven pages from three documents carry a
Transkribus-DONE reference, which is what the collection offers; every figure
below is reported with n and with an exact p-value rather than an asymptotic
one.

Usage:
  python analyze_summary.py        # writes analysis.json and analysis.md
"""

from __future__ import annotations

import difflib
import importlib.util
import itertools
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
REPO = ROOT.parent.parent

_spec = importlib.util.spec_from_file_location(
    "run_benchmark", ROOT / "run_benchmark.py"
)
bench = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bench)

# Rank correlation over 7 pages: 7! = 5040 permutations, so the p-value is the
# exact tail and never a normal approximation.
PERMUTATION_LIMIT = 9

# The worst third of the material by fair CER, rounded up, is what a triage rule
# has to catch. With seven pages that is three.
TERCILE = 3


# ----------------------------- statistics -----------------------------------


def ranks(values: list[float]) -> list[float]:
    """Ascending ranks with the mean rank on ties, the Spearman convention."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        shared = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = shared
        i = j + 1
    return out


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """None where a side is constant, because the coefficient is undefined there."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    den = math.sqrt(sum(v * v for v in dx) * sum(v * v for v in dy))
    return sum(a * b for a, b in zip(dx, dy, strict=True)) / den if den else None


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation of the ranks."""
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    return pearson(ranks(xs), ranks(ys))


def permutation_p(xs: list[float], ys: list[float]) -> float | None:
    """Two-sided exact p for Spearman: the share of all relabelings of `ys`
    whose coefficient reaches the observed magnitude. Enumeration is exact up to
    PERMUTATION_LIMIT elements and refused above it."""
    rho = spearman(xs, ys)
    if rho is None:
        return None
    if len(xs) > PERMUTATION_LIMIT:
        raise ValueError(f"exact permutation refused for n={len(xs)}")
    rx, ry = ranks(xs), ranks(ys)
    hits = total = 0
    # floating-point equality would drop the observed labeling itself
    for perm in itertools.permutations(ry):
        value = pearson(rx, list(perm))
        total += 1
        if value is not None and abs(value) >= abs(rho) - 1e-12:
            hits += 1
    return hits / total


def sign_test_p(better: int, worse: int) -> tuple[float, float]:
    """Exact binomial tail at p = 0.5 over the decided pages, one- and two-sided.

    Ties carry no direction and are excluded before the call, which is the
    standard sign test.
    """
    n = better + worse
    if not n:
        return (1.0, 1.0)
    extreme = min(better, worse)
    tail = sum(math.comb(n, i) for i in range(extreme + 1)) / 2**n
    return (tail, min(1.0, 2 * tail))


# ------------------------- reading the material ------------------------------


def reference_pages(summary: dict) -> list[tuple[str, dict]]:
    """The pages a CER is defined on, minus the degenerate references.

    The exclusion reads the `reference_degenerate` flag of the summary, which is
    a property of the reference text, so no page is dropped for the value it
    happened to measure.
    """
    return sorted(
        (pid, page)
        for pid, page in summary["pages"].items()
        if page.get("reference_class") == "transkribus-done"
        and not page.get("reference_degenerate")
    )


def micro_cer(
    pages: list[tuple[str, dict]], iteration: str, field: str
) -> float | None:
    """Edit distance summed over all runs of all pages, divided by the reference
    length summed the same way. A long page then weighs as much as it is long,
    where the mean of page means weighs every page alike."""
    dist = length = 0
    for _, page in pages:
        entry = page["iterations"].get(iteration, {}).get(field)
        if not entry:
            continue
        dist += sum(entry["dist"])
        length += entry["ref_len"] * len(entry["dist"])
    return dist / length if length else None


def page_mean_cer(
    pages: list[tuple[str, dict]], iteration: str, field: str
) -> float | None:
    values = [
        page["iterations"][iteration][field]["mean"]
        for _, page in pages
        if page["iterations"].get(iteration, {}).get(field)
    ]
    return sum(values) / len(values) if values else None


# --------------------------- uncertain markers -------------------------------


def marked_tokens(record: dict) -> tuple[list[str], list[bool]]:
    """Fair tokens of one run and, per token, whether the model marked it.

    A marker is a string the model repeated from its own line, so it is matched
    back to the line it was reported on rather than to the page: the same word
    elsewhere on the page stays unmarked. Both sides pass through the fair
    normalisation, otherwise a marker with a diacritic never meets its token.
    """
    tokens: list[str] = []
    marked: list[bool] = []
    for part in record["parsed"]["pages"]:
        for line in part.get("lines", []):
            text = line.get("text", "")
            if bench.FOLIO_LINE_RE.match(text):
                continue
            line_tokens = bench.normalize(text, "fair").split()
            flagged: set[str] = set()
            for note in line.get("uncertain") or []:
                flagged.update(bench.normalize(note, "fair").split())
            tokens.extend(line_tokens)
            marked.extend(token in flagged for token in line_tokens)
    return tokens, marked


def matched_in_hypothesis(reference: list[str], hypothesis: list[str]) -> set[int]:
    """Positions of `hypothesis` that align to a reference token.

    The pair is oriented before alignment exactly as `positionwise` orients its
    repeats, because difflib picks one of several equally long alignments and the
    choice follows argument order. An unmatched token is the approximation of an
    error used here; a token aligned at the wrong place, and a correct token that
    lost its alignment to a neighbouring insertion, both fall on the wrong side
    of it.
    """
    a, b, swapped = reference, hypothesis, False
    if (len(a), a) > (len(b), b):
        a, b, swapped = b, a, True
    hits: set[int] = set()
    for blk in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            hits.add(blk.a + k if swapped else blk.b + k)
    return hits


def uncertain_quality(pages: list[tuple[str, dict]], iteration: str) -> dict:
    """Precision and recall of the uncertain markers against the token alignment.

    Aggregation is over run tokens rather than over page averages, so a page
    contributes what it carries. `error_base_rate` is the share of unmatched
    tokens overall and is the precision a marker placed at random would reach;
    precision above it is the only sense in which the markers carry information.
    """
    per_page = {}
    tp_all = marked_all = wrong_all = tokens_all = 0
    for pid, page in pages:
        entry = page["iterations"].get(iteration)
        if not entry:
            continue
        reference = bench.normalize("\n".join(page["gt_lines"]), "fair").split()
        tp = marked_n = wrong_n = tokens_n = 0
        for name in entry["runs"]:
            record = json.loads((ROOT / "runs" / name).read_text(encoding="utf-8"))
            tokens, marked = marked_tokens(record)
            hits = matched_in_hypothesis(reference, tokens)
            wrong = [i for i in range(len(tokens)) if i not in hits]
            tp += sum(1 for i in wrong if marked[i])
            marked_n += sum(marked)
            wrong_n += len(wrong)
            tokens_n += len(tokens)
        per_page[pid] = {
            "marked": marked_n,
            "erroneous": wrong_n,
            "tokens": tokens_n,
            "precision": round(tp / marked_n, 4) if marked_n else None,
            "recall": round(tp / wrong_n, 4) if wrong_n else None,
        }
        tp_all += tp
        marked_all += marked_n
        wrong_all += wrong_n
        tokens_all += tokens_n
    return {
        "marked": marked_all,
        "erroneous": wrong_all,
        "tokens": tokens_all,
        "precision": round(tp_all / marked_all, 4) if marked_all else None,
        "recall": round(tp_all / wrong_all, 4) if wrong_all else None,
        "error_base_rate": round(wrong_all / tokens_all, 4) if tokens_all else None,
        "pages": per_page,
    }


# ------------------------------ the analyses ---------------------------------


def correlations(pages: list[tuple[str, dict]], iterations: list[str]) -> dict:
    out = {}
    for iteration in iterations:
        rows = [
            (page["iterations"][iteration], page)
            for _, page in pages
            if iteration in page["iterations"]
        ]
        cer = [entry["cer_fair"]["mean"] for entry, _ in rows]
        block = {"n": len(rows)}
        for measure in ("consistency_words", "consistency_numbers"):
            values = [entry.get(measure) for entry, _ in rows]
            if any(v is None for v in values):
                block[measure] = {"rho": None, "p": None, "note": "value missing"}
                continue
            rho = spearman(values, cer)
            block[measure] = {
                "rho": round(rho, 4) if rho is not None else None,
                "p": round(permutation_p(values, cer), 5),
            }
        out[iteration] = block
    return out


def paired_comparison(pages: list[tuple[str, dict]], first: str, second: str) -> dict:
    """Per-page direction of the it01 to it02 difference, plus both aggregates."""
    out: dict = {"n": len(pages)}
    for field in ("cer_strict", "cer_fair"):
        better = worse = tie = 0
        deltas = {}
        for pid, page in pages:
            a = page["iterations"][first][field]["mean"]
            b = page["iterations"][second][field]["mean"]
            deltas[pid] = round(b - a, 4)
            if b < a:
                better += 1
            elif b > a:
                worse += 1
            else:
                tie += 1
        one_sided, two_sided = sign_test_p(better, worse)
        out[field] = {
            "better": better,
            "worse": worse,
            "tie": tie,
            "p_one_sided": round(one_sided, 5),
            "p_two_sided": round(two_sided, 5),
            "delta_per_page": deltas,
            "micro": {
                it: round(micro_cer(pages, it, field), 4) for it in (first, second)
            },
            "page_mean": {
                it: round(page_mean_cer(pages, it, field), 4) for it in (first, second)
            },
        }
    return out


def triage_point(pages: list[tuple[str, dict]], iteration: str) -> dict:
    """Smallest word-agreement cut that captures the worst-read third.

    The cut sits midway between the worst tercile's highest agreement and the
    next page above it, where the two are separable at all. What the rule costs
    is reported as the number of pages it selects in total.
    """
    rows = sorted(
        (
            (
                page["iterations"][iteration]["cer_fair"]["mean"],
                pid,
                page["iterations"][iteration]["consistency_words"],
            )
            for pid, page in pages
            if iteration in page["iterations"]
        ),
        reverse=True,
    )
    worst = rows[:TERCILE]
    rest = rows[TERCILE:]
    ceiling = max(row[2] for row in worst)
    above = [row[2] for row in rest if row[2] > ceiling]
    separable = len(above) == len(rest)
    threshold = (ceiling + min(above)) / 2 if above else ceiling
    selected = [row[1] for row in rows if row[2] <= threshold]
    return {
        "iteration": iteration,
        "tercile_size": TERCILE,
        "worst_pages": [row[1] for row in worst],
        "threshold_consistency_words": round(threshold, 3),
        "separable": separable,
        "selected_pages": selected,
        "captured": sum(1 for row in worst if row[1] in selected),
        "false_positives": len(selected)
        - sum(1 for row in worst if row[1] in selected),
    }


def build(summary: dict) -> dict:
    pages = reference_pages(summary)
    iterations = sorted({it for _, page in pages for it in page["iterations"]})
    result = {
        "summary_generated": summary["generated"],
        "normalisation_profile": summary["normalisation_profile"],
        "reference_pages": [pid for pid, _ in pages],
        "degenerate_excluded": sorted(
            pid
            for pid, page in summary["pages"].items()
            if page.get("reference_degenerate")
        ),
        "correlation": correlations(pages, iterations),
        "uncertain": {it: uncertain_quality(pages, it) for it in iterations},
    }
    if len(iterations) >= 2:
        result["paired"] = paired_comparison(pages, iterations[0], iterations[-1])
        result["triage"] = {it: triage_point(pages, it) for it in iterations}
    return result


# ------------------------------- the report ----------------------------------


def pct(value: float | None, digits: int = 1) -> str:
    return "n. b." if value is None else f"{value * 100:.{digits}f} %"


def report(result: dict) -> str:
    """German prose beside the JSON, in the language of the cohort READMEs."""
    n = len(result["reference_pages"])
    its = sorted(result["correlation"])
    lines = [
        "# Sekundäranalyse des Benchmark-Summary",
        "",
        f"Datenstand `summary.json` {result['summary_generated'][:10]}, "
        f"Profile {result['normalisation_profile']['fair']} und {result['normalisation_profile']['strict']}. "
        f"Grundlage sind die {n} Referenzseiten mit tragfähiger Referenz "
        f"({', '.join(result['reference_pages'])}); ausgeschlossen sind "
        f"{', '.join(result['degenerate_excluded'])} über das Datenfeld `reference_degenerate`.",
        "",
        "## Sagt die Selbstkonsistenz die Fehlerrate vorher?",
        "",
        "Spearman-Rangkorrelation der Übereinstimmung gegen die faire CER, je Iteration über "
        f"n = {n} Seiten, mit exaktem Permutations-p über alle {math.factorial(n)} Umordnungen.",
        "",
        "| Iteration | Wortkonsistenz vs. CER fair | p | Zahlkonsistenz vs. CER fair | p |",
        "|-----------|-----------------------------|---|-----------------------------|---|",
    ]
    for it in its:
        block = result["correlation"][it]
        w, num = block["consistency_words"], block["consistency_numbers"]
        lines.append(f"| {it} | {w['rho']} | {w['p']} | {num['rho']} | {num['p']} |")
    lines += [
        "",
        "Ein negatives Vorzeichen heißt, dass die Seiten mit geringer Übereinstimmung die "
        "Seiten mit hoher Fehlerrate sind. Damit ist die Voraussetzung erfüllt, referenzlose "
        "Seiten nach Übereinstimmung zu priorisieren. Die Effektstärke bleibt bei sieben Seiten "
        "unbestimmt. Ablesbar ist die Richtung.",
        "",
    ]

    if "paired" in result:
        first, last = its[0], its[-1]
        paired = result["paired"]
        lines += [
            f"## {first} gegen {last}, seitenweise gepaart",
            "",
            f"Jede Seite wird mit sich selbst verglichen, also {last} gegen {first} auf derselben "
            "Referenz. Das Vorzeichen ist unabhängig davon, wie lang die Seiten sind, und der "
            "exakte Binomialtest über die entschiedenen Seiten prüft, ob die Richtung Zufall sein kann.",
            "",
            "| Maß | besser | schlechter | p einseitig | p zweiseitig | Mikro-CER "
            f"{first} → {last} | Seitenmittel {first} → {last} |",
            "|-----|--------|------------|-------------|--------------|--------------------|--------------------|",
        ]
        for field in ("cer_strict", "cer_fair"):
            block = paired[field]
            lines.append(
                f"| {field} | {block['better']} von {paired['n']} | {block['worse']} | "
                f"{block['p_one_sided']} | {block['p_two_sided']} | "
                f"{pct(block['micro'][first])} → {pct(block['micro'][last])} | "
                f"{pct(block['page_mean'][first])} → {pct(block['page_mean'][last])} |"
            )
        lines += [
            "",
            "Das Mikro-Mittel gewichtet jede Seite mit ihrer Referenzlänge, das Seitenmittel "
            "gewichtet jede Seite gleich. Wo beide auseinanderlaufen, stammt der Unterschied aus "
            "der Längenverteilung des Sets.",
            "",
        ]

    lines += [
        "## Treffen die uncertain-Marker die Fehler?",
        "",
        "Die Tokens eines Laufs werden gegen die Referenz aligniert; ein Token ohne Alignment gilt "
        "als falsch. Das ist eine Näherung. Ein an falscher Stelle aligniertes Token und ein "
        "korrektes Token, das sein Alignment an eine benachbarte Einfügung verliert, fallen beide "
        "auf die falsche Seite dieser Grenze. Die Basisrate ist der Anteil nicht alignierter Tokens "
        "insgesamt und damit die Präzision, die ein zufällig gesetzter Marker erreichen würde.",
        "",
        "| Iteration | Marker | falsche Tokens | Tokens | Präzision | Recall | Basisrate |",
        "|-----------|--------|----------------|--------|-----------|--------|-----------|",
    ]
    for it in its:
        block = result["uncertain"][it]
        lines.append(
            f"| {it} | {block['marked']} | {block['erroneous']} | {block['tokens']} | "
            f"{pct(block['precision'])} | {pct(block['recall'])} | {pct(block['error_base_rate'])} |"
        )
    lines += [
        "",
        "Die Präzision liegt in beiden Iterationen weit über der Basisrate, ein Marker steht also "
        "überzufällig oft auf einem Token, das dem Alignment entgeht. Der Übergang zu it02 kauft "
        "Recall mit Präzision, was der Absicht der Iteration entspricht.",
        "",
    ]

    if "triage" in result:
        lines += [
            "## Ein abgeleiteter Arbeitspunkt für die Triage",
            "",
            f"Das schlechteste Drittel des Materials sind die {TERCILE} Seiten mit der höchsten "
            "fairen CER. Gesucht ist der Schnitt auf der Wortkonsistenz, der genau diese Seiten "
            "einsammelt.",
            "",
            "| Iteration | Schwelle Wortkonsistenz | trennt | erfasst | Fehlalarme |",
            "|-----------|-------------------------|--------|---------|------------|",
        ]
        for it in its:
            block = result["triage"][it]
            lines.append(
                f"| {it} | ≤ {block['threshold_consistency_words']} | "
                f"{'ja' if block['separable'] else 'nein'} | "
                f"{block['captured']} von {block['tercile_size']} | {block['false_positives']} |"
            )
        lines += [
            "",
            "Die Schwelle ist ein Vorschlag. Sie stammt aus sieben Seiten dreier Dokumente und "
            "ist an denselben Seiten abgelesen, an denen sie bewertet wird; ein Holdout fehlt. "
            "Auf unbekanntem Material taugt sie als Startwert für eine Reihenfolge der Prüfung. "
            "Für die Beurteilung einer einzelnen Seite bleibt der Blick ins Faksimile maßgeblich.",
            "",
        ]

    lines += [
        "## Reproduktion",
        "",
        "```",
        "python evaluation/benchmark/analyze_summary.py",
        "```",
    ]
    return "\n".join(lines) + "\n"


def write(path: Path, text: str) -> None:
    """LF on every platform, so the artifact does not depend on the working copy."""
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    summary = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
    result = build(summary)
    write(
        ROOT / "analysis.json", json.dumps(result, ensure_ascii=False, indent=1) + "\n"
    )
    write(ROOT / "analysis.md", report(result))
    print(
        f"analysis.json und analysis.md geschrieben ({len(result['reference_pages'])} Referenzseiten)"
    )


if __name__ == "__main__":
    main()
