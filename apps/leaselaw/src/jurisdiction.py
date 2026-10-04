"""Resolve legal_city for sample addresses (mailing city ≠ legal city)."""

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

_POSTAL_TO_LEGAL = {
    ("CA", "san ysidro"): "San Diego",
    ("CA", "van nuys"): "Los Angeles",
    ("CA", "west hollywood"): "Los Angeles",
}

_COUNTY_BY_CITY: dict[tuple[str, str], str] = {
    ("CA", "Los Angeles"): "Los Angeles County",
    ("CA", "San Francisco"): "San Francisco County",
    ("CA", "San Diego"): "San Diego County",
    ("CA", "Berkeley"): "Alameda County",
    ("CA", "Santa Ana"): "Orange County",
    ("NJ", "Hoboken"): "Hudson County",
    ("NJ", "Jersey City"): "Hudson County",
    ("NJ", "Newark"): "Essex County",
    ("MA", "Boston"): "Suffolk County",
    ("MA", "Cambridge"): "Middlesex County",
}


def legal_city_for(postal_city: str | None, state: str | None) -> str | None:
    if not postal_city:
        return None
    city = postal_city.strip()
    st = (state or "").upper()
    key = (st, city.lower())
    if key in _POSTAL_TO_LEGAL:
        return _POSTAL_TO_LEGAL[key]
    if st == "MA" and city.lower() in _BOSTON_NEIGHBORHOODS:
        return "Boston"
    return city


def county_for(legal_city: str | None, state: str | None) -> str | None:
    if not legal_city or not state:
        return None
    return _COUNTY_BY_CITY.get((state.upper(), legal_city))


def attach_legal_city(addr: dict) -> dict:
    out = dict(addr)
    legal = legal_city_for(out.get("postal_city"), out.get("state"))
    out["legal_city"] = legal
    out["city"] = legal or out.get("postal_city")
    county = county_for(legal, out.get("state"))
    stack = [out.get("state")]
    if county:
        stack.append(county)
    stack.append(legal or out.get("postal_city"))
    out["jurisdiction_stack"] = [x for x in stack if x]
    out["county"] = county
    return out
