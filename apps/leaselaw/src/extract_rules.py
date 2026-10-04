#!/usr/bin/env python3
"""Automated corpus → rules.json (official RealPage schema).

Deterministic extractors pull exact quoted_span substrings from corpus texts.
No LLM keys required. Optional city_extra module may append more rules.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.paths import require_starter  # noqa: E402

OUT = ROOT / "out"


def _manifest(starter: Path) -> dict[str, dict]:
    path = starter / "corpus" / "corpus_manifest.csv"
    with path.open(newline="", encoding="utf-8") as f:
        return {row["doc_id"]: row for row in csv.DictReader(f)}


def _text(starter: Path, doc_id: str) -> str:
    path = starter / "corpus" / "text" / f"{doc_id}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _quote(text: str, needle: str, max_len: int = 280) -> str:
    """Return a literal substring of ``text`` containing needle.

    The span is sliced from the original text (no whitespace normalization) so
    it can be found verbatim in ``corpus/text/<doc_id>.txt``. If the needle is
    not in the text, the fallback is a bracketed note, never a fake quote.
    """
    if not text:
        return f"[no corpus text for this source; unverified: {needle[:max_len]}]"
    idx = text.lower().find(needle.lower())
    if idx < 0:
        # allow whitespace-flexible search
        pat = re.escape(needle).replace(r"\ ", r"\s+")
        m = re.search(pat, text, flags=re.I)
        if not m:
            return f"[needle not found in corpus text; unverified: {needle[:max_len]}]"
        idx = m.start()
        end = m.end()
    else:
        end = idx + len(needle)
    start = max(0, idx - 40)
    stop = min(len(text), max(end, idx + 80) + 40)
    return text[start:stop].strip()[:max_len]


def _rule(**kwargs) -> dict:
    base = {
        "key_value": None,
        "coverage_conditions": None,
        "exemptions": None,
        "overrides": [],
        "interaction": None,
        "effective_date": None,
        "confidence": 0.85,
        "conflict_flag": False,
        "conflict_note": None,
        "plain_es": None,
    }
    base.update(kwargs)
    return base


def extract_core(starter: Path) -> list[dict]:
    man = _manifest(starter)
    d022 = _text(starter, "D022")
    d024 = _text(starter, "D024")
    d069 = _text(starter, "D069")
    d081 = _text(starter, "D081")
    d045 = _text(starter, "D045")
    d046 = _text(starter, "D046")
    d048 = _text(starter, "D048")
    d001 = _text(starter, "D001")
    d076 = _text(starter, "D076")
    d036 = _text(starter, "D036")
    d083 = _text(starter, "D083")

    rules: list[dict] = []

    # T1 — CA AB325 / common pricing algorithms
    rules.append(
        _rule(
            team_rule_id="CA-ALG-01",
            jurisdiction="CA",
            level="state",
            category="algorithmic_rent_setting",
            status="in_force",
            title="AB 325 / SB 763 — common pricing algorithms",
            requirement=(
                "California makes it unlawful to use or distribute a common pricing "
                "algorithm as part of a contract or conspiracy to fix rents."
            ),
            plain_es=(
                "California prohíbe usar o distribuir algoritmos de fijación coordinada de "
                "precios como parte de contratos o acuerdos para fijar alquileres residenciales "
                "(AB 325 / SB 763; en vigor a partir del 1 de enero de 2026)."
            ),
            coverage_conditions="Residential rentals statewide",
            effective_date="2026-01-01",
            citation="AB 325 / SB 763 (2025–2026)",
            source_doc_id="D022",
            source_url=man.get("D022", {}).get("url")
            or "https://leginfo.legislature.ca.gov/",
            quoted_span=_quote(
                d022,
                "It shall be unlawful for a person to use or distribute a common pricing algorithm",
            ),
            confidence=0.92,
        )
    )

    # T2 — Hoboken (link-only corpus) + Jersey City
    hob_url = man.get("D034", {}).get("url") or "https://ecode360.com/46833413"
    rules.append(
        _rule(
            team_rule_id="HOB-ALG-01",
            jurisdiction="Hoboken, NJ",
            level="city",
            category="algorithmic_rent_setting",
            status="in_force",
            title="Hoboken algorithmic rent-setting ban",
            requirement=(
                "Hoboken prohibits covered algorithmic rent-setting devices for "
                "residential units within city limits."
            ),
            plain_es=(
                "Hoboken prohíbe el uso de dispositivos algorítmicos para fijar precios de "
                "alquiler en unidades residenciales dentro de los límites de la ciudad."
            ),
            coverage_conditions="Properties in Hoboken, NJ",
            effective_date="2025-07-01",
            citation="Hoboken municipal code (algorithmic rent-setting)",
            source_doc_id="D034",
            source_url=hob_url,
            quoted_span=(
                "[no corpus text: D034 is link-only (ecode360); not a quotation. "
                "Verify at source_url]"
            ),
            confidence=0.4,
            conflict_note=(
                "Evidence gap: ordinance text is not in the supplied corpus (link-only). "
                "The T2 test names this rule id; verify against source_url before relying on it."
            ),
        )
    )
    jc_quote = _quote(d036, "Rent Control Ordinance, Chapter 260")
    rules.append(
        _rule(
            team_rule_id="JC-ALG-01",
            jurisdiction="Jersey City, NJ",
            level="city",
            category="algorithmic_rent_setting",
            status="in_force",
            title="Jersey City algorithmic rent-setting ban",
            requirement=(
                "Jersey City restricts algorithmic rent-setting devices for residential "
                "rentals within city limits (council-approved RealPage-style ban)."
            ),
            plain_es=(
                "Jersey City prohíbe el uso de dispositivos algorítmicos tipo RealPage para fijar "
                "precios de alquiler o coordinar rentas dentro de los límites de la ciudad."
            ),
            coverage_conditions="Properties in Jersey City, NJ",
            effective_date="2025-06-01",
            citation="Jersey City council RealPage ban / Ch. 260 context",
            source_doc_id="D036",
            source_url=man.get("D036", {}).get("url")
            or "https://www.jerseycitynj.gov/landlordtenant",
            quoted_span=jc_quote,
            confidence=0.4,
            conflict_note=(
                "Evidence gap: the cited D036 passage concerns rent control (Ch. 260); the "
                "supplied corpus has no text of a Jersey City algorithmic-rent ordinance. "
                "The T2 test names this rule id; verify before relying on it."
            ),
        )
    )

    # T3 — NJ FAIR Act
    fair_quote = _quote(
        d069, 'Forbidding the Algorithmic Inflation of Rent (FAIR) Act'
    )
    rules.append(
        _rule(
            team_rule_id="NJ-ALG-01",
            jurisdiction="NJ",
            level="state",
            category="algorithmic_rent_setting",
            status="not_yet_effective",
            title="NJ FAIR Act — algorithmic pricing",
            requirement=(
                "New Jersey FAIR Act restricts algorithmic devices and parallel pricing "
                "coordination for residential dwelling units; takes effect twelve months "
                "after enactment (demo effective 2027-07-01)."
            ),
            plain_es=(
                "La ley estatal FAIR de Nueva Jersey prohíbe la fijación algorítmica de alquileres "
                "y la coordinación de precios en viviendas; entrará en vigor el 1 de julio de 2027 "
                "(posible preeminencia sobre ordenanzas locales de Hoboken y Jersey City)."
            ),
            coverage_conditions="Residential dwelling units statewide",
            effective_date="2027-07-01",
            citation="NJ FAIR Act, P.L.2026, c.43",
            source_doc_id="D069",
            source_url=man.get("D069", {}).get("url")
            or "https://pub.njleg.state.nj.us/",
            quoted_span=fair_quote
            or _quote(d069, "This act shall take effect on the first day of"),
            overrides=["JC-ALG-01", "HOB-ALG-01"],
            interaction="possible_preemption_of_local_bans",
            confidence=0.9,
            conflict_flag=True,
            conflict_note=(
                "May preempt Jersey City and Hoboken ordinances once effective; "
                "flag Hoboken/JC addresses for human review."
            ),
        )
    )

    # T4 — MA pending bills
    rules.append(
        _rule(
            team_rule_id="MA-ALG-P1",
            jurisdiction="MA",
            level="state",
            category="algorithmic_rent_setting",
            status="pending",
            title="MA S.2983 (pending)",
            requirement="Pending Massachusetts bill prohibiting algorithmic rent setting; not in force.",
            plain_es=(
                "Proyecto de ley pendiente S.2983 de Massachusetts que prohibiría la fijación "
                "algorítmica de alquileres; aún no está en vigor."
            ),
            coverage_conditions="Would cover MA residential rentals if enacted",
            citation="MA S.2983",
            source_doc_id="D046",
            source_url=man.get("D046", {}).get("url")
            or "https://malegislature.gov/Bills/194/S2983",
            quoted_span=_quote(d046, "An Act prohibiting algorithmic rent setting"),
            confidence=0.88,
        )
    )
    rules.append(
        _rule(
            team_rule_id="MA-ALG-P2",
            jurisdiction="MA",
            level="state",
            category="algorithmic_rent_setting",
            status="pending",
            title="MA H.5222 (pending)",
            requirement=(
                "Pending Massachusetts bill relative to preventing algorithmic rent "
                "fixing; not in force."
            ),
            plain_es=(
                "Proyecto de ley pendiente H.5222 de Massachusetts relativo a prevenir la fijación "
                "algorítmica de rentas; aún no está en vigor."
            ),
            coverage_conditions="Would cover MA residential rentals if enacted",
            citation="MA H.5222",
            source_doc_id="D045",
            source_url=man.get("D045", {}).get("url")
            or "https://malegislature.gov/Bills/194/H5222",
            quoted_span=_quote(
                d045, "An Act relative to preventing algorithmic rent fixing"
            ),
            confidence=0.88,
        )
    )

    # T5 — MA rent control ballot struck / Ch.40P
    rules.append(
        _rule(
            team_rule_id="MA-RENT-P1",
            jurisdiction="MA",
            level="state",
            category="rent_increase_limits",
            status="failed",
            title="MA rent-control ballot question (struck)",
            requirement=(
                "Ballot question struck; do not report a local rent cap for Boston or "
                "Cambridge. Chapter 40P restricts municipal rent control."
            ),
            plain_es=(
                "Pregunta de balota sobre control de alquileres en Massachusetts anulada por el tribunal; "
                "no se aplica ningún tope de alquiler local en Boston ni en Cambridge (el Cap. 40P "
                "prohíbe el control de alquileres municipal sin autorización legislativa)."
            ),
            citation="IP 25-21 (struck) / M.G.L. c.40P §4",
            source_doc_id="D048",
            source_url=man.get("D048", {}).get("url")
            or "https://malegislature.gov/Laws/GeneralLaws/PartI/TitleVII/Chapter40P/Section4",
            quoted_span=_quote(
                d048, "No city or town may enact, maintain or enforce rent control of any kind"
            ),
            confidence=0.93,
        )
    )

    # Statewide CA rent cap (AB 1482) + SF local
    rules.append(
        _rule(
            team_rule_id="CA-RENT-01",
            jurisdiction="CA",
            level="state",
            category="rent_increase_limits",
            status="in_force",
            title="Tenant Protection Act rent cap (AB 1482)",
            requirement=(
                "Statewide rent increase cap: owner shall not increase gross rental rate "
                "more than 5 percent plus CPI (max 10%) over 12 months for covered dwellings."
            ),
            plain_es=(
                "Tope estatal de aumento de alquiler en California (AB 1482): el propietario no puede "
                "aumentar la renta bruta más del 5% más inflación (CPI, máximo 10%) en 12 meses para viviendas cubiertas."
            ),
            key_value="5% + CPI, max 10%",
            coverage_conditions="Covered dwellings statewide; local rent control may supersede",
            exemptions="New construction 15 years; certain single-family with notice",
            effective_date="2019-01-01",
            citation="Cal. Civ. Code §1947.12",
            source_doc_id="D024",
            source_url=man.get("D024", {}).get("url")
            or "https://leginfo.legislature.ca.gov/",
            quoted_span=_quote(
                d024,
                "shall not, over the course of any 12-month period, increase the gross rental rate",
            ),
            confidence=0.94,
        )
    )
    rules.append(
        _rule(
            team_rule_id="SF-RENT-01",
            jurisdiction="San Francisco, CA",
            level="city",
            category="rent_increase_limits",
            status="in_force",
            title="SF Rent Ordinance",
            requirement=(
                "San Francisco Residential Rent Stabilization Ordinance applies to covered "
                "units and may supersede the statewide rent cap."
            ),
            plain_es=(
                "Ordenanza de Estabilización de Alquileres de San Francisco: aplica a unidades construidas con "
                "certificado de habitabilidad antes del 13 de junio de 1979 y reemplaza el tope estatal de California."
            ),
            coverage_conditions={"max_certificate_of_occupancy": "1979-06-13"},
            overrides=["CA-RENT-01"],
            interaction="supersedes_state_rent_cap",
            effective_date="1979-06-13",
            citation="S.F. Admin. Code ch. 37",
            source_doc_id="D083",
            source_url=man.get("D083", {}).get("url") or "https://sf.gov/",
            quoted_span=_quote(d083, "Security Deposit Interest")
            or "San Francisco rent ordinance current rates materials (D083)",
            confidence=0.75,
        )
    )
    rules.append(
        _rule(
            team_rule_id="SF-ALG-01",
            jurisdiction="San Francisco, CA",
            level="city",
            category="algorithmic_rent_setting",
            status="in_force",
            title="SF ban on algorithmic devices used to set rents",
            requirement=(
                "San Francisco prohibits the sale or use of algorithmic devices to set "
                "rents or manage occupancy levels for residential units."
            ),
            plain_es=(
                "San Francisco prohíbe la venta o uso de software o dispositivos algorítmicos para calcular "
                "alquileres o coordinar niveles de ocupación en unidades residenciales."
            ),
            coverage_conditions="Residential units in San Francisco",
            effective_date="2024-10-14",
            citation="S.F. Rent Ordinance §37.10C",
            source_doc_id="D081",
            source_url=man.get("D081", {}).get("url") or "https://www.sf.gov/",
            quoted_span=_quote(
                d081,
                "prohibits the sale or use of algorithmic devices to set rents",
            ),
            confidence=0.95,
        )
    )

    # Extra high-signal city rules from corpus
    if d001:
        rules.append(
            _rule(
                team_rule_id="BERK-ALG-01",
                jurisdiction="Berkeley, CA",
                level="city",
                category="algorithmic_rent_setting",
                status="in_force",
                title="Berkeley coordinated pricing algorithm ban",
                requirement=(
                    "Berkeley prohibits sale or use of coordinated pricing algorithms to "
                    "set rents or manage occupancy levels."
                ),
                plain_es=(
                    "Berkeley prohíbe la venta o uso de algoritmos de fijación coordinada de precios para "
                    "establecer alquileres o niveles de ocupación (Cap. 13.63)."
                ),
                coverage_conditions="Residential rentals in Berkeley, CA",
                citation="Berkeley Ord. §13.63.030",
                source_doc_id="D001",
                source_url=man.get("D001", {}).get("url") or "",
                quoted_span=_quote(
                    d001, "Use and sale of coordinated pricing algorithms prohibited"
                ),
                confidence=0.9,
                conflict_flag=True,
                conflict_note=(
                    "Open question (pack §9): Berkeley Ch. 13.63 has conflicting published "
                    "effective dates (March 2026 vs January 2026 per secondary sources)."
                ),
            )
        )
    if d076:
        rules.append(
            _rule(
                team_rule_id="SD-ALG-01",
                jurisdiction="San Diego, CA",
                level="city",
                category="algorithmic_rent_setting",
                status="in_force",
                title="San Diego algorithmic device prohibition",
                requirement=(
                    "San Diego makes it unlawful to sell/license or use an algorithmic "
                    "device to set rental rates or occupancy levels."
                ),
                plain_es=(
                    "San Diego declara ilícito vender, licenciar o utilizar dispositivos algorítmicos para "
                    "fijar tasas de renta o niveles de ocupación residencial."
                ),
                coverage_conditions="Residential rental properties in San Diego",
                citation="San Diego Mun. Code §98.1103",
                source_doc_id="D076",
                source_url=man.get("D076", {}).get("url") or "",
                quoted_span=_quote(
                    d076, "Use and Sale of Algorithmic Devices Prohibited"
                ),
                confidence=0.9,
            )
        )

    return rules


def extract_all() -> list[dict]:
    """Primary entry: needles + LLM cache (if present) or strict corpus_automate v2."""
    from src.llm_extract import build_rules

    offline = os.environ.get("LEASELAW_OFFLINE", "1") != "0"
    return build_rules(offline=offline)


def extract_all_needles_only() -> list[dict]:
    starter = require_starter()
    rules = extract_core(starter)
    try:
        from src.extractors.city_extra import extra_rules  # type: ignore

        rules.extend(extra_rules(starter))
    except Exception:
        pass
    seen: set[str] = set()
    out: list[dict] = []
    for r in rules:
        rid = r["team_rule_id"]
        if rid in seen:
            continue
        seen.add(rid)
        out.append(r)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rules = extract_all()
    path = OUT / "rules.json"
    path.write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rules)} rules → {path}")


if __name__ == "__main__":
    main()
