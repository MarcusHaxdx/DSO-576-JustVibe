"""Read numeric fact values from an XBRL instance, to check the numbers an agent cites."""
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

_LINKBASE = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml")
_NUMBER = re.compile(r"(?<![\w.])-?\(?\$?\d[\d,]*(?:\.\d+)?\)?")


def instance_path(folder: Path) -> Path:
    """The one .xml file in a filing folder that is not a linkbase."""
    found = [p for p in Path(folder).glob("*.xml") if not p.name.endswith(_LINKBASE)]
    if len(found) != 1:
        raise ValueError(f"expected one instance document in {folder}, found {len(found)}")
    return found[0]


@lru_cache(maxsize=256)
def fact_values(folder: str) -> frozenset:
    """Absolute values of every numeric fact (an element with a unitRef) in the instance."""
    values = set()
    for _, el in ET.iterparse(instance_path(Path(folder))):
        if el.get("unitRef") is not None and el.text:
            try:
                values.add(abs(float(el.text.strip())))
            except ValueError:
                pass
        el.clear()
    return frozenset(values)


def cited_numbers(text: str) -> list:
    """Absolute values of the numbers in a sentence, skipping small whole numbers (counts,
    line numbers) and years. Decimals are kept, so rates and per-share values are checked."""
    out = []
    for tok in _NUMBER.findall(text or ""):
        s = tok.strip("()$-").replace("$", "").replace(",", "")
        try:
            v = abs(float(s))
        except ValueError:
            continue
        plain_int = "," not in tok and "." not in tok
        if plain_int and (v < 100 or 1900 <= v <= 2100):
            continue
        out.append(v)
    return out
