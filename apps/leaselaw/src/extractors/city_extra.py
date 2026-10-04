#!/usr/bin/env python3
"""Additional official-schema city rules pulled verbatim from the corpus.

Owner: OpenCode (`opencode/mimo-v2.6-flash-free`).
`extract_rules.extract_all()` imports :func:`extra_rules` and merges the list
into the core rules (de-dup by ``team_rule_id``, first record wins), so every id
below is deliberately *new* — the core extractor already emits ``BERK-ALG-01``,
``SD-ALG-01``, ``SF-ALG-01``.

Guarantees for each returned record:

* ``quoted_span`` is a **literal substring** of ``corpus/text/<doc_id>.txt``
  (asserted in :func:`_record` — a record is dropped rather than invented if
  the needle cannot be located);
* ``source_doc_id`` / ``source_url`` come straight from
  ``corpus/corpus_manifest.csv``;
* fields follow ``schema/rule_record.schema.json`` (enum categories/statuses,
  ``quoted_span`` length ≥ 20).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

try:  # normal import path: `src.extractors.city_extra`
    from ..paths import require_starter
except ImportError:  # pragma: no cover - direct/script import fallback
    from src.paths import require_starter  # type: ignore

MIN_QUOTE = 20


# --------------------------------------------------------------------------- #
# corpus helpers
# --------------------------------------------------------------------------- #
def _manifest(starter: Path) -> dict[str, dict[str, str]]:
    path = starter / "corpus" / "corpus_manifest.csv"
    with path.open(newline="", encoding="utf-8") as f:
        return {row["doc_id"]: row for row in csv.DictReader(f)}


def _text(starter: Path, doc_id: str) -> str:
    path = starter / "corpus" / "text" / f"{doc_id}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _span(text: str, needle: str) -> str | None:
    """Return a verbatim substring of ``text`` covering ``needle``.

    The corpus texts are hard-wrapped, so an exact ``str.find`` may miss; the
    fallback pattern joins the needle's words with ``\\s+``. Either way the
    returned slice is cut from the *original* text (only leading/trailing
    whitespace is trimmed away), so ``span in text`` always holds.
    """
    if not text or not needle:
        return None
    idx = text.find(needle)
    if idx >= 0:
        start, end = idx, idx + len(needle)
    else:
        pattern = r"\s+".join(re.escape(word) for word in needle.split())
        m = re.search(pattern, text, flags=re.I)
        if not m:
            return None
        start, end = m.start(), m.end()
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    span = text[start:end]
    if len(span) < MIN_QUOTE or span not in text:
        return None
    return span


def _base(**fields) -> dict:
    """Official schema record with the same nullable defaults as extract_core."""
    record = {
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
    record.update(fields)
    return record


def _record(
    starter: Path,
    man: dict[str, dict[str, str]],
    doc_id: str,
    needle: str,
    **fields,
) -> dict | None:
    """Build one rule; return ``None`` if the quote or manifest URL is missing."""
    row = man.get(doc_id) or {}
    source_url = (row.get("url") or "").strip()
    span = _span(_text(starter, doc_id), needle)
    if not source_url or span is None:
        return None
    record = _base(**fields)
    record["source_doc_id"] = doc_id
    record["source_url"] = source_url
    record["quoted_span"] = span
    return record


# --------------------------------------------------------------------------- #
# rule definitions
# --------------------------------------------------------------------------- #
def _berkeley(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D001 — Ordinance 7,992-N.S. §13.63.030(B): landlord *use* prohibition.
    rec = _record(
        starter,
        man,
        "D001",
        "It shall be unlawful for a landlord to use a coordinated pricing algorithm "
        "described in subsection A when setting rents or occupancy levels for "
        "residential dwelling units in the City of Berkeley.",
        team_rule_id="BERK-ALG-02",
        jurisdiction="Berkeley, CA",
        level="city",
        category="algorithmic_rent_setting",
        status="in_force",
        title="Berkeley §13.63.030(B) — landlord use of coordinated pricing algorithms",
        requirement=(
            "Berkeley landlords may not use a coordinated pricing algorithm when "
            "setting rents or occupancy levels for residential dwelling units in the "
            "city; each separate month and each separate dwelling unit is a separate "
            "violation."
        ),
        coverage_conditions="Residential dwelling units in the City of Berkeley",
        citation="Berkeley Mun. Code §13.63.030(B) (Ord. 7,992-N.S.)",
        confidence=0.9,
    )
    if rec:
        out.append(rec)

    # D001 — §13.63.040(B): private tenant action, $1,000 civil penalties.
    rec = _record(
        starter,
        man,
        "D001",
        "An aggrieved tenant may file a civil action for violations of section "
        "13.63.030, subsection B, for injunctive relief, money damages, and/or civil "
        "penalties of up to $1,000 per violation.",
        team_rule_id="BERK-ALG-03",
        jurisdiction="Berkeley, CA",
        level="city",
        category="algorithmic_rent_setting",
        status="in_force",
        title="Berkeley §13.63.040 — tenant private action and penalties",
        requirement=(
            "An aggrieved tenant may sue over a §13.63.030(B) violation and recover "
            "injunctive relief, money damages, and civil penalties up to $1,000 per "
            "violation; the City Attorney may bring the parallel civil action under "
            "§13.63.040(A)."
        ),
        key_value="$1,000 per violation (civil penalty)",
        coverage_conditions="Residential dwelling units in the City of Berkeley",
        citation="Berkeley Mun. Code §13.63.040 (Ord. 7,992-N.S.)",
        confidence=0.88,
    )
    if rec:
        out.append(rec)

    # D005 — screening fee cap + rights statement (application_screening_fees).
    rec = _record(
        starter,
        man,
        "D005",
        "The maximum tenant screening fee for 2026 is $68.96",
        team_rule_id="BERK-SCR-01",
        jurisdiction="Berkeley, CA",
        level="city",
        category="application_screening_fees",
        status="in_force",
        title="Berkeley tenant screening fee cap (2026) + rights statement",
        requirement=(
            "Berkeley landlords may charge no more than the published 2026 tenant "
            "screening fee cap ($68.96), must hand over a copy of the credit report within "
            "7 days plus an itemized receipt, and must accept a reusable screening report "
            "if the applicant provides one."
        ),
        key_value="$68.96 maximum tenant screening fee (2026)",
        coverage_conditions="Prospective tenants applying for Berkeley residential property",
        exemptions=(
            "No fee if no rental unit is actually available; fees must be returned to "
            "applicants not selected unless applications are reviewed in order and the "
            "first qualified applicant gets the unit (BMC 13.78.010)."
        ),
        citation="Berkeley Mun. Code §13.78.010 (tenant screening fees)",
        confidence=0.88,
        conflict_flag=True,
        conflict_note=(
            "Open question (pack §9): California's screening-fee cap under Cal. Civ. Code § 1950.6 "
            "has no single official 2026 dollar figure published statewide; Berkeley caps at $68.96 "
            "while inflation adjustments vary across jurisdictions."
        ),
        plain_es=(
            "Los propietarios de Berkeley no pueden cobrar más del tope de tarifa de evaluación de $68.96 "
            "(2026) y deben entregar copia del informe crediticio; existe incertidumbre estatal (pregunta abierta "
            "del pack §9) sobre la cifra única oficial aplicable en toda California."
        ),
    )
    if rec:
        out.append(rec)

    # D005 — no non-refundable renewal / roommate fees (BMC 13.78.016).
    rec = _record(
        starter,
        man,
        "D005",
        "cannot charge a non-refundable fee to any existing tenant for the purpose of "
        "renewing a tenancy",
        team_rule_id="BERK-SCR-02",
        jurisdiction="Berkeley, CA",
        level="city",
        category="application_screening_fees",
        status="in_force",
        title="Berkeley ban on non-refundable renewal & roommate fees (BMC 13.78.016)",
        requirement=(
            "A Berkeley owner or agent cannot charge an existing tenant a non-refundable "
            "fee to renew a tenancy, in whole or in part, including fees tied to a "
            "roommate's departure or to adding or replacing a roommate."
        ),
        coverage_conditions="Existing tenancies on Berkeley residential rental property",
        citation="Berkeley Mun. Code §13.78.016",
        confidence=0.88,
    )
    if rec:
        out.append(rec)

    # D007 — security deposit cap (AB 12) (security_deposits).
    rec = _record(
        starter,
        man,
        "D007",
        "Starting July 1, 2024, many landlords may only charge one month's rent for "
        "unfurnished and furnished units",
        team_rule_id="BERK-DEP-01",
        jurisdiction="Berkeley, CA",
        level="city",
        category="security_deposits",
        status="in_force",
        title="Berkeley security deposit cap — one month's rent (AB 12)",
        requirement=(
            "Starting July 1, 2024 most Berkeley landlords may charge only one month's "
            "rent as a security deposit for unfurnished and furnished units, and the last "
            "month's rent counts as part of the deposit; any remaining portion must be "
            "returned within 21 days."
        ),
        key_value="1 month's rent (AB 12, from 2024-07-01)",
        coverage_conditions="Berkeley residential rental property",
        exemptions=(
            "Owners of only two rental properties with four units or fewer total may "
            "charge up to two months' rent when ownership is held by a natural person, "
            "family trust, or all-natural-person LLC."
        ),
        effective_date="2024-07-01",
        citation="Cal. Civ. Code §1950.6 (AB 12) — Berkeley Rent Board",
        confidence=0.9,
    )
    if rec:
        out.append(rec)

    # D003 — Fair Chance Access to Housing (screening_restrictions).
    rec = _record(
        starter,
        man,
        "D003",
        "The Fair Chance Access to Housing Ordinance prohibits rental housing providers "
        "in Berkeley from asking about and using criminal history and/or criminal "
        "background checks in their rental housing advertising, applications, tenant "
        "selection process, or decision-making",
        team_rule_id="BERK-FC-01",
        jurisdiction="Berkeley, CA",
        level="city",
        category="screening_restrictions",
        status="in_force",
        title="Berkeley Fair Chance Access to Housing Ordinance (BMC 13.106)",
        requirement=(
            "Berkeley rental housing providers may not ask about or use criminal history "
            "or background checks in advertising, applications, tenant selection, or "
            "decision-making, and may not demand a higher deposit or rent based on "
            "criminal history."
        ),
        coverage_conditions="Advertising, applications, and tenant selection in Berkeley",
        exemptions=(
            "Limited exemptions apply (lifetime sex offenders; public housing / Section 8 "
            "properties) — see the Ordinance for specifics (BMC 13.106)."
        ),
        effective_date="2020-04-14",
        citation="Berkeley Mun. Code §13.106 (Ronald V. Dellums Fair Chance Ordinance)",
        confidence=0.9,
    )
    if rec:
        out.append(rec)

    # D004 — 2026 relocation assistance amounts (just_cause_eviction).
    rec = _record(
        starter,
        man,
        "D004",
        "The standard relocation assistance payment will increase to $19,413",
        team_rule_id="BERK-RELOC-01",
        jurisdiction="Berkeley, CA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="Berkeley relocation assistance — 2026 published amounts",
        requirement=(
            "Under the Rent Stabilization and Good Cause for Eviction Ordinance and the "
            "Ellis Implementation Ordinance, Berkeley owners must pay indexed relocation "
            "assistance on owner move-in and Ellis Act evictions; for 2026 the standard "
            "payment is $19,413 and the additional payment for qualifying households is "
            "$6,471."
        ),
        key_value="$19,413 standard / $6,471 additional (2026)",
        coverage_conditions="Owner move-in and Ellis Act evictions in Berkeley",
        effective_date="2026-01-01",
        citation="Berkeley Rent Board — 2026 Adjustments of Relocation Assistance Payments",
        confidence=0.87,
    )
    if rec:
        out.append(rec)
    return out


def _san_diego(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D076 — §98.1102: definition carve-outs (reporting tools).
    rec = _record(
        starter,
        man,
        "D076",
        "(a) A software or product used by a person to publish reports regarding "
        "rental rates or occupancy levels from aggregated historical nonpublic "
        "competitor data that is more than 90 days old, or from information "
        "available to the general public, and does not recommend rental rates or "
        "occupancy levels for future residential rental property leases or renewals.",
        team_rule_id="SD-ALG-02",
        jurisdiction="San Diego, CA",
        level="city",
        category="algorithmic_rent_setting",
        status="in_force",
        title="San Diego §98.1102 — what is not an “algorithmic device”",
        requirement=(
            "San Diego's algorithmic-device ban does not reach software that only "
            "publishes reports from aggregated historical nonpublic competitor data "
            "more than 90 days old or from public information, so long as it does not "
            "recommend rents for future leases or renewals."
        ),
        coverage_conditions="Algorithmic-device definition, San Diego Mun. Code Div. 11",
        exemptions=(
            "Also excluded: software used to establish rental rates or income limits "
            "under local, state, or federal affordable-housing program guidelines "
            "(§98.1102(b))."
        ),
        citation="San Diego Mun. Code §98.1102 (O-2025-107)",
        confidence=0.85,
    )
    if rec:
        out.append(rec)

    # D076 — §98.1104: tenant remedies.
    rec = _record(
        starter,
        man,
        "D076",
        "A tenant may seek injunctive relief, damages, or civil penalties of up to "
        "$1,000 per violation of this Division, in a civil action against a landlord.",
        team_rule_id="SD-ALG-03",
        jurisdiction="San Diego, CA",
        level="city",
        category="algorithmic_rent_setting",
        status="in_force",
        title="San Diego §98.1104 — tenant remedies for algorithmic price-fixing",
        requirement=(
            "A tenant may recover injunctive relief, damages, or civil penalties of up "
            "to $1,000 per violation, plus costs and reasonable attorney's fees; a lease "
            "clause limiting those fees is unenforceable."
        ),
        key_value="$1,000 per violation (civil penalty)",
        coverage_conditions="Residential rental property in San Diego",
        citation="San Diego Mun. Code §98.1104 (O-2025-107)",
        confidence=0.88,
    )
    if rec:
        out.append(rec)

    # D073 — Residential Tenant Protections: just cause for termination.
    rec = _record(
        starter,
        man,
        "D073",
        "Division protects the rights of tenants by requiring just cause for termination "
        "of a tenancy consistent with California Civil Code section 1946.2",
        team_rule_id="SD-JUST-01",
        jurisdiction="San Diego, CA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="San Diego Residential Tenant Protections — just cause for termination",
        requirement=(
            "San Diego's Residential Tenant Protections (Div. 7) require just cause for "
            "termination of a tenancy consistent with Civil Code §1946.2, limit the "
            "grounds for termination, and require relocation assistance in specified "
            "circumstances."
        ),
        coverage_conditions="Residential tenancies in the City of San Diego",
        citation="San Diego Mun. Code ch. 9, art. 8, div. 7 §98.0701 (O-21647 N.S.)",
        confidence=0.87,
    )
    if rec:
        out.append(rec)
    return out


def _san_francisco(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D081 — enforcement: tenant or City Attorney civil action.
    rec = _record(
        starter,
        man,
        "D081",
        "The law prohibits the sale or use of such algorithmic devices and allows a "
        "tenant or the City Attorney to bring a civil action if they believe an "
        "entity is in violation of the law.",
        team_rule_id="SF-ALG-02",
        jurisdiction="San Francisco, CA",
        level="city",
        category="algorithmic_rent_setting",
        status="in_force",
        title="SF Rent Ordinance §37.10C — tenant / City Attorney enforcement",
        requirement=(
            "A tenant or the City Attorney may bring a civil action against an entity "
            "that sells or uses an algorithmic device to set rents or manage occupancy "
            "levels for residential units in San Francisco."
        ),
        coverage_conditions="Residential units in San Francisco",
        effective_date="2024-10-14",
        citation="S.F. Rent Ordinance §37.10C",
        confidence=0.9,
    )
    if rec:
        out.append(rec)

    # D081 — scope: definition of a covered "algorithmic device".
    rec = _record(
        starter,
        man,
        "D081",
        "means a device such as a software program that uses algorithms to analyze "
        "nonpublic competitor rental data for the purposes of providing a landlord "
        "recommendations on what rent to charge for a vacant unit",
        team_rule_id="SF-ALG-03",
        jurisdiction="San Francisco, CA",
        level="city",
        category="algorithmic_rent_setting",
        status="in_force",
        title="SF Rent Ordinance §37.10C — “algorithmic device” definition",
        requirement=(
            "Software that analyzes nonpublic competitor rental data to give a landlord "
            "a recommendation on the rent to charge for a vacant unit is a covered "
            "algorithmic device under San Francisco law."
        ),
        coverage_conditions="Residential units in San Francisco",
        effective_date="2024-10-14",
        citation="S.F. Rent Ordinance §37.10C",
        confidence=0.87,
    )
    if rec:
        out.append(rec)

    # D079 — just cause requirement for Rent Ordinance units.
    rec = _record(
        starter,
        man,
        "D079",
        'In order to evict a tenant from a rental unit covered by the Rent Ordinance, a '
        'landlord must have a "just cause" reason that is the dominant motive for '
        'pursuing the eviction.',
        team_rule_id="SF-JUST-01",
        jurisdiction="San Francisco, CA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="SF Rent Ordinance §37.9 — just cause required for covered units",
        requirement=(
            "To evict a tenant from a Rent Ordinance-covered unit, a landlord must have a "
            "'just cause' reason that is the dominant motive for the eviction; mere lease "
            "expiration or a change of ownership is not just cause."
        ),
        coverage_conditions={"max_certificate_of_occupancy": "1979-06-13"},
        citation="S.F. Rent Ordinance §37.9 (Overview of Just Cause Evictions)",
        confidence=0.9,
    )
    if rec:
        out.append(rec)

    # D080 — published annual allowable increase for the current window.
    rec = _record(
        starter,
        man,
        "D080",
        "the annual allowable increase amount effective March 1, 2026 through "
        "February 28, 2027 is 1.6%",
        team_rule_id="SF-RENT-02",
        jurisdiction="San Francisco, CA",
        level="city",
        category="rent_increase_limits",
        status="in_force",
        title="SF annual allowable increase — 1.6% (Mar 1, 2026 – Feb 28, 2027)",
        requirement=(
            "For rent-controlled units the annual allowable increase for the window "
            "March 1, 2026 through February 28, 2027 is 1.6%; the Rent Board publishes a "
            "new percentage for each annual window."
        ),
        key_value="1.6% (Mar 1, 2026 – Feb 28, 2027)",
        coverage_conditions={"max_certificate_of_occupancy": "1979-06-13"},
        effective_date="2026-03-01",
        citation="S.F. Rent Board — Annual Rent Increase for 3/1/26 – 2/28/27",
        confidence=0.9,
    )
    if rec:
        out.append(rec)
    return out


def _los_angeles(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []
    rso_coverage = {"max_certificate_of_occupancy": "1978-10-01"}

    # D040 — Just Cause For Eviction Ordinance (JCO).
    rec = _record(
        starter,
        man,
        "D040",
        "It prohibits terminations of tenancies without just cause and requires "
        "relocation assistance for no-fault evictions.",
        team_rule_id="LA-JCO-01",
        jurisdiction="Los Angeles, CA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="LA Just Cause For Eviction Ordinance (JCO)",
        requirement=(
            "The JCO prohibits terminating tenancies without just cause and requires "
            "relocation assistance for no-fault evictions for most City of Los Angeles "
            "residential property that is not regulated by the Rent Stabilization "
            "Ordinance."
        ),
        key_value="Just cause required; relocation pay on no-fault evictions",
        coverage_conditions=(
            "City of Los Angeles residential property not regulated by the RSO; "
            "tenancy of six months or original lease expired, whichever comes first"
        ),
        exemptions=(
            "Units regulated by the RSO are outside the JCO (see LA-RSO-01). Also "
            "excluded: transient hotels, licensed care facilities, fraternity/sorority "
            "houses, owner's roommate, certain nonprofit facilities, and "
            "HACLA/government-owned property (LAHD JCO page)."
        ),
        citation="City of Los Angeles Just Cause For Eviction Ordinance (LAHD)",
        confidence=0.85,
    )
    if rec:
        out.append(rec)

    # D040 — nonpayment eviction floor: rent owed must exceed Fair Market Rent.
    rec = _record(
        starter,
        man,
        "D040",
        "Effective March 27, 2023, landlords may not evict a tenant who falls behind "
        "in rent unless the tenant owes an amount higher than the Fair Market Rent (FMR)",
        team_rule_id="LA-JCO-02",
        jurisdiction="Los Angeles, CA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="LA nonpayment evictions — rent owed must exceed Fair Market Rent",
        requirement=(
            "For every RSO and JCO rental unit in Los Angeles, a landlord may not evict "
            "for nonpayment unless the tenant owes more than the Fair Market Rent for "
            "the unit's bedroom size."
        ),
        key_value="Rent owed must exceed Fair Market Rent (FMR)",
        coverage_conditions="All RSO & JCO rental units in the City of Los Angeles",
        effective_date="2023-03-27",
        citation="LAHD — Evictions for Non-Payment of Rent (RSO & JCO)",
        confidence=0.85,
    )
    if rec:
        out.append(rec)

    # D041 — RSO overview: annual allowable increase + pre-1979 coverage.
    rec = _record(
        starter,
        man,
        "D041",
        "Rent may be increased once every 12 months by the allowable rent increase "
        "percentage",
        team_rule_id="LA-RSO-01",
        jurisdiction="Los Angeles, CA",
        level="city",
        category="rent_increase_limits",
        status="in_force",
        title="LA Rent Stabilization Ordinance — annual allowable increase",
        requirement=(
            "Rental property first built on or before October 1, 1978 may receive a rent "
            "increase only once every 12 months and only at the LAHD allowable "
            "percentage; increases needing LAHD approval are listed separately by LAHD."
        ),
        key_value="Once every 12 months (LAHD allowable %)",
        coverage_conditions=rso_coverage,
        exemptions=(
            "Units first built after October 1, 1978 are outside the RSO and fall under "
            "the Just Cause Ordinance (LA-JCO-01)."
        ),
        # No `overrides` here: engine.apply_supersession() marks CA-RENT-01 superseded
        # whenever this row is *present*, even when the row itself resolves to
        # "unknown" (post-1979 LA stock) — which would hide the AB 1482 cap that does
        # apply there. Supersession stays with SF-RENT-01, whose coverage always
        # resolves to "applies" inside its jurisdiction.
        citation="L.A. Mun. Code ch. XV (RSO) — LAHD RSO overview",
        confidence=0.85,
        plain_es=(
            "Las unidades residenciales construidas en o antes del 1 de octubre de 1978 "
            "en Los Ángeles están sujetas a la ordenanza RSO; los aumentos de alquiler se limitan "
            "a una vez cada 12 meses según el porcentaje fijado por LAHD."
        ),
    )
    if rec:
        out.append(rec)

    # D042 — RSO rent increase calculator: published 3% window.
    rec = _record(
        starter,
        man,
        "D042",
        "Annual rent increases for rental units subject to the City of Los Angeles Rent "
        "Stabilization Ordinance (RSO), effective July 1, 2025, through June 30, 2026",
        team_rule_id="LA-RSO-02",
        jurisdiction="Los Angeles, CA",
        level="city",
        category="rent_increase_limits",
        status="in_force",
        title="LA RSO allowable increase — 3% (Jul 1, 2025 – Jun 30, 2026)",
        requirement=(
            "For the LAHD-published window July 1, 2025 through June 30, 2026 the maximum "
            "annual allowable rent increase for RSO units is 3%; LAHD sets a new percentage "
            "each July, so confirm the current window before relying on the figure."
        ),
        key_value="3% (Jul 1, 2025 – Jun 30, 2026)",
        coverage_conditions=rso_coverage,
        effective_date="2025-07-01",
        citation="LAHD RSO Rent Increase Calculator",
        confidence=0.82,
        conflict_flag=True,
        conflict_note=(
            "Open question (pack §9): Los Angeles's new RSO formula has two published "
            "effective dates: 2026-02-02 per LAHD vs 2026-01-24 per landlord association."
        ),
        plain_es=(
            "El aumento anual permitido bajo LA RSO para la ventana actual es del 3%; "
            "existe discrepancia documentada en fuentes oficiales (pregunta abierta §9) sobre "
            "si la nueva fórmula RSO rige desde el 2026-02-02 (LAHD) o el 2026-01-24 (asociación de arrendadores)."
        ),
    )
    if rec:
        out.append(rec)

    # D043 — no-fault relocation assistance + Declaration of Intent to Evict.
    rec = _record(
        starter,
        man,
        "D043",
        "All tenant not- at-fault evictions require payment of relocation assistance and "
        "the filing of a Declaration of Intent to Evict form",
        team_rule_id="LA-RELOC-01",
        jurisdiction="Los Angeles, CA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="LA relocation assistance for no-fault evictions (RSO & JCO)",
        requirement=(
            "Every no-fault (not-at-fault) eviction of an RSO or JCO tenant requires "
            "payment of relocation assistance and filing a Declaration of Intent to Evict "
            "with the LA Housing Department before the tenant may be served with a "
            "termination notice."
        ),
        key_value="Relocation assistance + LAHD Declaration of Intent to Evict",
        coverage_conditions="RSO- and JCO-covered units in the City of Los Angeles",
        exemptions=(
            "Notices may only be served after the landlord files the Declaration with "
            "LAHD; a copy must be filed within 3 days of service."
        ),
        citation="LAHD Relocation Assistance Bulletin (A & B)",
        confidence=0.88,
    )
    if rec:
        out.append(rec)
    return out


def _boston(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D014 — Housing Stability Notification Act: notice of tenants' rights.
    rec = _record(
        starter,
        man,
        "D014",
        "requires any landlord planning to end a tenancy agreement to provide the tenant "
        "with a Notice",
        team_rule_id="BOS-HSNA-01",
        jurisdiction="Boston, MA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="Boston Housing Stability Notification Act (HSNA)",
        requirement=(
            "A Boston landlord ending a tenancy must give the tenant a Notice of Tenants' "
            "Rights and Resources at the same time as the Notice to Quit, and must send a "
            "copy of the Notice to Quit together with a Certificate of Compliance/Service "
            "to the City's Office of Housing Stability."
        ),
        coverage_conditions="Residential tenancies in the City of Boston",
        citation="Boston HSNA (Ord. passed Oct. 2020) — City of Boston",
        confidence=0.87,
    )
    if rec:
        out.append(rec)

    # D012 — Boston Fair Housing Regulations: source-of-income discrimination.
    rec = _record(
        starter,
        man,
        "D012",
        "illegal to discriminate when renting, buying, selling, or securing financing "
        "for any housing",
        team_rule_id="BOS-FH-01",
        jurisdiction="Boston, MA",
        level="city",
        category="screening_restrictions",
        status="in_force",
        title="Boston Fair Housing Regulations — no source-of-income discrimination",
        requirement=(
            "It is illegal in Boston to discriminate in renting, buying, selling, or "
            "financing housing — including refusing a household because it uses rental "
            "assistance such as Section 8 vouchers."
        ),
        coverage_conditions="Rental, sale, and financing of housing in the City of Boston",
        exemptions="Protected classes listed by the Boston Fair Housing & Equity Commission",
        citation="Boston Fair Housing Regulations (BFHEC)",
        confidence=0.85,
    )
    if rec:
        out.append(rec)

    # D011 — H.3744 local-option rent stabilization petition (died in study).
    rec = _record(
        starter,
        man,
        "D011",
        "An Act petition for a special law authorizing the city of Boston to implement "
        "rent stabilization and tenant eviction protections",
        team_rule_id="BOS-RENT-P2",
        jurisdiction="Boston, MA",
        level="city",
        category="rent_increase_limits",
        status="failed",
        title="MA H.3744 — Boston rent stabilization local option (not law)",
        requirement=(
            "A local-option petition that would authorize the City of Boston to adopt "
            "rent stabilization; it was referred to the Joint Committee on Housing and "
            "accompanied by a study order, so no Boston rent cap exists. Do not report a "
            "rent cap for Boston addresses."
        ),
        key_value="No Boston rent cap (bill in study / not enacted)",
        coverage_conditions="Would cover City of Boston residential rentals if enacted",
        citation="MA H.3744 (193rd General Court)",
        confidence=0.86,
    )
    if rec:
        out.append(rec)
    return out


def _cambridge(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D029 — Cambridge Fair Housing Ordinance, ch. 14.04.
    rec = _record(
        starter,
        man,
        "D029",
        "The Fair Housing Ordinance prohibits discrimination in real estate transactions "
        "such as",
        team_rule_id="CAM-FH-01",
        jurisdiction="Cambridge, MA",
        level="city",
        category="screening_restrictions",
        status="in_force",
        title="Cambridge Fair Housing Ordinance (ch. 14.04)",
        requirement=(
            "The Cambridge Fair Housing Ordinance prohibits discrimination in real estate "
            "transactions — including advertising housing in a discriminatory manner — and "
            "the Human Rights Commission investigates and adjudicates those complaints."
        ),
        coverage_conditions="Real estate transactions in Cambridge, MA",
        citation="Cambridge Fair Housing Ordinance, ch. 14.04",
        confidence=0.85,
    )
    if rec:
        out.append(rec)
    return out


def _jersey_city(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D036 — Rent Control Ordinance ch. 260 exemption for small properties.
    rec = _record(
        starter,
        man,
        "D036",
        "All 1-4 Unit Properties are exempt from rent control",
        team_rule_id="JC-RENT-01",
        jurisdiction="Jersey City, NJ",
        level="city",
        category="rent_increase_limits",
        status="in_force",
        title="Jersey City Rent Control Ordinance (Ch. 260) — small-property exemption",
        requirement=(
            "Jersey City's Rent Control Ordinance (Ch. 260) regulates covered rental "
            "property, but all 1-4 unit properties are exempt from rent control; verify a "
            "property's rent control status with the City before applying a cap."
        ),
        coverage_conditions="Jersey City rental property subject to Ch. 260 status determination",
        exemptions="All 1-4 unit properties are exempt from rent control (Ch. 260)",
        citation="Jersey City Rent Control Ordinance, Ch. 260",
        confidence=0.8,
    )
    if rec:
        out.append(rec)
    return out


def _new_jersey(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D067 — Truth in Renting: 30-day return of the security deposit.
    rec = _record(
        starter,
        man,
        "D067",
        "Within 30 days after the termination of a tenancy, a landlord must return the "
        "security deposit, plus interest earned less deductions, to the tenant",
        team_rule_id="NJ-DEP-01",
        jurisdiction="NJ",
        level="state",
        category="security_deposits",
        status="in_force",
        title="NJ security deposit return within 30 days (Truth in Renting)",
        requirement=(
            "Within 30 days after a tenancy ends, a New Jersey landlord must return the "
            "security deposit plus interest, less lawful deductions, by personal delivery, "
            "registered mail, or certified mail, with an itemized list of any deductions."
        ),
        key_value="30 days after termination",
        coverage_conditions="Residential tenancies statewide in New Jersey",
        citation="N.J.S.A. 46:8-21.1 (Truth in Renting)",
        confidence=0.88,
    )
    if rec:
        out.append(rec)

    # D067 — double damages for late/withheld returns.
    rec = _record(
        starter,
        man,
        "D067",
        "If a landlord fails to return the security deposit within 30 days, or the tenant "
        "disagrees with the amount deducted, the tenant may sue for double the amount",
        team_rule_id="NJ-DEP-02",
        jurisdiction="NJ",
        level="state",
        category="security_deposits",
        status="in_force",
        title="NJ double-damages remedy for withheld security deposits",
        requirement=(
            "If a landlord fails to return the security deposit within 30 days, or the "
            "tenant disputes the deductions, the tenant may sue for double the amount of "
            "the security deposit."
        ),
        key_value="Double the security deposit",
        coverage_conditions="Residential tenancies statewide in New Jersey",
        citation="N.J.S.A. 46:8-26 (Truth in Renting)",
        confidence=0.88,
    )
    if rec:
        out.append(rec)
    return out


def _santa_ana(starter: Path, man: dict) -> list[dict]:
    out: list[dict] = []

    # D085 — Rent Stabilization Ordinance: lower of 3% or 80% of CPI.
    rec = _record(
        starter,
        man,
        "D085",
        "Increase in residential rents are limited to the lower of 3% per year, or 80% of "
        "the percent change in the Consumer Price Index over the most recent 12-month period",
        team_rule_id="SA-RSO-01",
        jurisdiction="Santa Ana, CA",
        level="city",
        category="rent_increase_limits",
        status="in_force",
        title="Santa Ana Rent Stabilization Ordinance — 3% / 80% CPI cap",
        requirement=(
            "Residential rent increases in Santa Ana are limited to the lower of 3% per "
            "year or 80% of the 12-month CPI change; if CPI is negative no increase is "
            "permitted."
        ),
        key_value="Lower of 3% or 80% of 12-month CPI",
        coverage_conditions="Residential rental property in Santa Ana, CA",
        effective_date="2021-11-19",
        citation="Santa Ana Rent Stabilization Ordinance (eff. Nov 19, 2021)",
        confidence=0.87,
    )
    if rec:
        out.append(rec)

    # D084 — published current-year maximum allowable increase.
    rec = _record(
        starter,
        man,
        "D084",
        "2.87 percent is the maximum allowable rent increase for the period of "
        "September 1, 2026 through August 31, 2027",
        team_rule_id="SA-RSO-02",
        jurisdiction="Santa Ana, CA",
        level="city",
        category="rent_increase_limits",
        status="in_force",
        title="Santa Ana allowable increase — 2.87% (Sep 1, 2026 – Aug 31, 2027)",
        requirement=(
            "For the City-published window September 1, 2026 through August 31, 2027 the "
            "maximum allowable rent increase for rent-stabilized Santa Ana units is 2.87%; "
            "the City republishes the figure annually."
        ),
        key_value="2.87% (Sep 1, 2026 – Aug 31, 2027)",
        coverage_conditions="Rent-stabilized units in Santa Ana, CA",
        effective_date="2026-09-01",
        citation="City of Santa Ana — Current Maximum Allowable Rent Increase",
        confidence=0.85,
    )
    if rec:
        out.append(rec)

    # D085 — Just Cause Eviction Ordinance.
    rec = _record(
        starter,
        man,
        "D085",
        "a Just Cause Eviction Ordinance, which limits the allowed reasons for which a "
        "renter can be evicted",
        team_rule_id="SA-JCO-01",
        jurisdiction="Santa Ana, CA",
        level="city",
        category="just_cause_eviction",
        status="in_force",
        title="Santa Ana Just Cause Eviction Ordinance",
        requirement=(
            "Santa Ana's Just Cause Eviction Ordinance limits the reasons for which a "
            "renter may be evicted, and certain no-fault evictions also require relocation "
            "assistance."
        ),
        coverage_conditions="Residential rentals in Santa Ana, CA",
        effective_date="2021-11-19",
        citation="Santa Ana Just Cause Eviction Ordinance (eff. Nov 19, 2021)",
        confidence=0.86,
    )
    if rec:
        out.append(rec)
    return out


def extra_rules(starter: Path | None = None) -> list[dict]:
    """Return additional official-schema rules sourced from corpus texts."""
    root = starter or require_starter()
    man = _manifest(root)
    rules: list[dict] = []
    for builder in (
        _berkeley,
        _san_diego,
        _san_francisco,
        _los_angeles,
        _boston,
        _cambridge,
        _jersey_city,
        _new_jersey,
        _santa_ana,
    ):
        rules.extend(builder(root, man))
    return rules


if __name__ == "__main__":  # pragma: no cover
    import json

    print(json.dumps(extra_rules(), indent=2, ensure_ascii=False))
