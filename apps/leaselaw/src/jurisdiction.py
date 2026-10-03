"""Resolve legal_city for sample addresses (mailing city ≠ legal city for Boston neighborhoods)."""

from __future__ import annotations

# Boston postal neighborhoods in the sample CSV → legal city Boston
_BOSTON_NEIGHBORHOODS = {
    "dorchester",
    "roxbury",
    "east boston",
    "brighton",
    "allston",
    "south boston",
    "jamaica plain",
    "charlestown",
    "hyde park",
    "mattapan",
    "roslindale",
    "west roxbury",
    "mission hill",
    "back bay",
    "beacon hill",
    "north end",
    "south end",
    "fenway",
    "kenmore",
}


def legal_city_for(postal_city: str | None, state: str | None) -> str | None:
    if not postal_city:
        return None
    city = postal_city.strip()
    st = (state or "").upper()
    if st == "MA" and city.lower() in _BOSTON_NEIGHBORHOODS:
        return "Boston"
    return city


def attach_legal_city(addr: dict) -> dict:
    out = dict(addr)
    legal = legal_city_for(out.get("postal_city"), out.get("state"))
    out["legal_city"] = legal
    out["city"] = legal or out.get("postal_city")
    stack = [out.get("state"), legal or out.get("postal_city")]
    out["jurisdiction_stack"] = [x for x in stack if x]
    return out
