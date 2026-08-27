# Vendored TEI schema

## tei_all.rng

- Source URL: https://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng
- Release: TEI P5 Version 4.12.0, generated from ODD source 2026-07-28, revision 113e933e2
- Edition location: https://www.tei-c.org/Vault/P5/4.12.0/
- Downloaded: 2026-08-27
- Licensing: dual-licensed by the TEI Consortium under CC BY 4.0 and BSD-2-Clause

The schema is vendored so that `pipeline/validate_tei.py` validates offline and against a
pinned TEI release rather than a moving `current` target. To upgrade, re-download from the
same URL and update the release line above.

## docta.rng

Hand-written in this repository, neither vendored nor generated. It pins the DoCTA encoding
contract, admitting exactly the elements, attributes and structures that
`pipeline/build_tei.py` emits, with the closed lists of the pipeline (responsibility ids, stream statuses, milestone
units, entity elements) enumerated and the id shapes given as patterns. Free text and values
that legitimately vary (titles, prose, dates, zone points, URLs) stay unconstrained.

The grammar is derived from the generator, so the generator is its source of truth. A change
to what `build_tei.py` emits is a change to this schema, and the two-stage run of
`validate_tei.py` is what keeps them in step. Being narrower than TEI, it never replaces
`tei_all.rng`; TEI conformance stays the first stage.

An ODD is the upgrade path. As soon as the project needs human-readable encoding guidelines
alongside the machine check, or a customisation that documents its own constraints, the
contract should be written as a TEI ODD and both the schema and the prose generated from it.
Until then a hand-written RelaxNG is the smaller instrument for the same check.
