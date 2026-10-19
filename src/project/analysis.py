"""Reusable pandas analysis for BUILD_SPEC.md (no UI or notebook execution).

Typical use::

    corpus = load_assertions()
    results = load_configurations()
    cases = filter_assertions(corpus, assertion_types=["126"])
    cards = assertion_summary(cases)
    shortlist = evaluate_criteria(results, min_acc=60, max_ser=0)

Loaders validate complete sources; transformations accept their filtered subsets.
Functions return new objects and never write files or mutate inputs. Configuration
aggregates and assertion records deliberately have no cross-source join API.
None means an unrestricted filter; an empty sequence matches nothing. Caller/UI
owns caching and session state. Reload after source changes to revalidate content.
"""

from collections.abc import Sequence
from hashlib import sha256
from io import BytesIO, StringIO
import json
from math import isfinite
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSERTION_PATH = PROJECT_ROOT / "data/raw/mathematical_reasoning.csv"
SOURCE_SHA256 = "fa52ccea5b80ea8ff1b27e5e38b5510caf74a82682858e1cc53641bbd1f7fdf2"
SOURCE_REVISION = "52d3ecb97e490a2392717935402cde283e8fa36e"
SOURCE_DOWNLOAD_DATE = "2026-10-05"
PAPER_URL = "https://arxiv.org/html/2605.14355v3"
ASSERTION_KEY = ("report.accession", "assertion.code", "assertion.detail")
CONFIGURATION_KEY = ("framework", "model")
RATE_COLUMNS = ("ACC_pct", "SER_pct", "EER_pct", "CER_pct")
ASSERTION_COLUMNS = (
    "assertion.code", "assertion.detail", "assertion.run-date",
    "assertion.severity", "assertion.source", "assertion.type", "entity.cik",
    "entity.name", "report.accepted-timestamp", "report.accession",
    "report.base-taxonomy", "report.creation-software", "report.document-type",
    "report.entry-url", "report.filing-date", "report.filing-year", "report.id",
    "report.sec-url", "report.sic-code", "folder_name",
)
SEARCH_COLUMNS = (
    "entity.name", "entity.cik", "report.accession", "assertion.code",
    "assertion.detail",
)
EXPECTED_CORPUS = {
    "assertions": 362, "filings": 158, "entities": 125, "rules": 61,
    "date_difference_records": 43,
}

# Auditing Table 2, transcribed in 01-cleaning.ipynb cell 16 and BUILD_SPEC.md.
# Percentages, not counts; aliases are preserved. These 65-instance aggregates
# cannot be mapped to the 362 local assertions. Never normalize rounding away.
_PUBLISHED_CSV = """framework,model,ACC_pct,SER_pct,EER_pct,CER_pct
ReAct Agent,sonnet,20.00,80.00,0.00,0.00
ReAct Agent,gpt,3.08,80.00,0.00,16.92
ReAct Agent,qwen397,15.38,80.00,0.00,4.62
ReAct Agent,qwen27,18.46,80.00,0.00,1.54
Claude Code,sonnet,66.15,0.00,6.15,27.69
Claude Code,gpt,44.62,0.00,6.15,49.23
Claude Code,qwen397,36.92,3.08,9.23,50.77
Claude Code,qwen27,43.08,0.00,12.31,44.62
Codex,sonnet,63.08,0.00,6.15,30.77
Codex,gpt,63.08,0.00,6.15,30.77
Codex,qwen397,49.23,0.00,6.15,44.62
Codex,qwen27,27.69,44.62,7.69,20.00
Hermes,sonnet,20.00,80.00,0.00,0.00
Hermes,gpt,20.00,80.00,0.00,0.00
Hermes,qwen397,20.00,80.00,0.00,0.00
Hermes,qwen27,16.92,80.00,0.00,3.08
OpenClaw,sonnet,66.15,0.00,6.15,27.69
OpenClaw,gpt,66.15,0.00,6.15,27.69
OpenClaw,qwen397,43.08,0.00,10.77,46.15
OpenClaw,qwen27,36.92,0.00,7.69,55.38
"""


class DataValidationError(ValueError):
    """An independent source is invalid; the UI should block its affected view."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise DataValidationError(message)


def _require_columns(frame: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = set(columns) - set(frame.columns)
    _require(not missing, f"Missing required columns: {sorted(missing)}")
    _require(frame.columns.is_unique, "Duplicate column names are not allowed.")


def validate_configurations(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the full 20-row source and return a typed copy (rates in 0–100)."""
    _require_columns(frame, (*CONFIGURATION_KEY, *RATE_COLUMNS, "audit_instances"))
    result = frame.copy(deep=True)
    _require(len(result) == 20, "Expected 20 published configurations.")
    for column in CONFIGURATION_KEY:
        _require(result[column].notna().all(), f"Missing {column}.")
        result[column] = result[column].astype("string")
        _require(result[column].str.strip().ne("").all(), f"Blank {column}.")
    _require(not result.duplicated(list(CONFIGURATION_KEY)).any(),
             "Duplicate framework/model key in configuration results.")
    for column in (*RATE_COLUMNS, "audit_instances"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
        _require(result[column].notna().all(), f"Invalid numeric values in {column}.")
    _require(result[list(RATE_COLUMNS)].apply(lambda c: c.between(0, 100)).all().all(),
             "Published rates must be finite percentages in [0, 100].")
    _require(result["audit_instances"].eq(65).all(),
             "Expected 65 audit instances per configuration.")
    _require(result[list(RATE_COLUMNS)].sum(axis=1).sub(100).abs().le(0.020000001).all(),
             "ACC/SER/EER/CER must sum to 100 within 0.02 percentage points.")
    result["audit_instances"] = result["audit_instances"].astype("Int64")
    return result


def load_configurations(path: str | Path | None = None) -> pd.DataFrame:
    """Load embedded published values, or validate an explicit replacement CSV.

    An external CSV must include audit_instances. It is never a fallback for an
    invalid source. Missing/read errors propagate with the affected file path.
    """
    if path is None:
        frame = pd.read_csv(StringIO(_PUBLISHED_CSV), dtype="string")
        frame["audit_instances"] = 65
    else:
        frame = pd.read_csv(Path(path), dtype="string", keep_default_na=False)
    result = validate_configurations(frame)
    result["source_reference"] = PAPER_URL
    return result


def prepare_assertions(raw: pd.DataFrame) -> pd.DataFrame:
    """Validate the full pinned-release structure and derive analysis columns.

    Original 20 fields remain exact strings for evidence/export. Parsed columns
    have a _parsed suffix; IDs hash the JSON-encoded full composite key. This
    function validates contents; load_assertions additionally validates bytes.
    """
    _require_columns(raw, ASSERTION_COLUMNS)
    _require(raw.shape == (362, 20), "Expected the pinned 362-row, 20-column corpus.")
    result = raw.astype("string").copy()
    _require(not result.isna().any().any(), "Corpus contains missing values.")
    _require(not result.apply(lambda c: c.str.strip().eq("")).any().any(),
             "Corpus contains blank fields.")
    _require(not result.duplicated(list(ASSERTION_KEY)).any(),
             "Duplicate assertion composite key.")
    for column in ("assertion.run-date", "report.filing-date", "report.accepted-timestamp"):
        date_format = "%Y-%m-%d %H:%M:%S" if column == "report.accepted-timestamp" else "%Y-%m-%d"
        parsed = pd.to_datetime(result[column], format=date_format, errors="coerce")
        _require(parsed.notna().all(), f"Failed date conversions in {column}.")
        result[f"{column}_parsed"] = parsed
    year = pd.to_numeric(result["report.filing-year"], errors="coerce")
    _require((year.notna() & year.mod(1).eq(0) & year.between(2022, 2024)).all(),
             "Invalid filing year; expected integer years 2022–2024.")
    result["report.filing-year_parsed"] = year.astype("Int64")
    filing_date = result["report.filing-date_parsed"]
    _require(year.eq(filing_date.dt.year).all(), "Filing year/date mismatch.")
    _require(result["assertion.run-date_parsed"].ge(filing_date).all(),
             "Assertion run date precedes filing date.")
    _require(result["report.accession"].str.fullmatch(r"\d{10}-\d{2}-\d{6}").all(),
             "Malformed accession identifier.")
    _require(result["entity.cik"].str.fullmatch(r"\d{1,10}").all(), "Malformed CIK.")
    result["accepted_date_differs"] = (
        result["report.accepted-timestamp_parsed"].dt.date.ne(filing_date.dt.date)
    )
    result["assertion_id"] = [
        sha256(json.dumps(list(key), ensure_ascii=False).encode("utf-8")).hexdigest()
        for key in result[list(ASSERTION_KEY)].itertuples(index=False, name=None)
    ]
    _require(result["assertion_id"].is_unique, "Assertion ID collision.")
    _require(assertion_summary(result) == EXPECTED_CORPUS,
             "Corpus counts differ from the pinned release's documented totals.")
    for column, expected in (
        ("report.document-type", {"10-K": 145, "10-Q": 217}),
        ("assertion.type", {"15": 116, "117": 136, "126": 110}),
    ):
        _require(result[column].value_counts().to_dict() == expected,
                 f"Unexpected category totals in {column}.")
    return result


def load_assertions(path: str | Path = ASSERTION_PATH) -> pd.DataFrame:
    """Read one byte snapshot, verify the pinned hash, then validate/prepare it."""
    path = Path(path)
    content = path.read_bytes()
    _require(sha256(content).hexdigest() == SOURCE_SHA256,
             f"SHA-256 mismatch for {path}; restore the pinned source release.")
    result = prepare_assertions(pd.read_csv(
        BytesIO(content), dtype="string", keep_default_na=False,
    ))
    result.attrs.update(source_path=str(path.resolve()), sha256=SOURCE_SHA256,
                        revision=SOURCE_REVISION, download_date=SOURCE_DOWNLOAD_DATE)
    return result


def _filter(frame: pd.DataFrame, selections: dict) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for column, values in selections.items():
        if values is not None:
            mask &= frame[column].isin(values)
    return frame.loc[mask].copy()


def filter_configurations(
    frame: pd.DataFrame, *, frameworks: Sequence[str] | None = None,
    models: Sequence[str] | None = None,
) -> pd.DataFrame:
    """OR within each selection, AND across selections; return a copy."""
    return _filter(frame, {"framework": frameworks, "model": models})


def rank_configurations(frame: pd.DataFrame, sort_by: str = "ACC_pct") -> pd.DataFrame:
    """Competition ACC ranks (1,1,3), with alphabetical tie display order.

    Error-rate sorts ascend; ACC descends; 'configuration' sorts alphabetically.
    ACC rank remains independent of the selected display sort.
    """
    if sort_by not in (*RATE_COLUMNS, "configuration"):
        raise ValueError(f"Unsupported configuration sort: {sort_by}")
    result = frame.copy()
    result["ACC_rank"] = result["ACC_pct"].rank(method="min", ascending=False).astype("Int64")
    columns = list(CONFIGURATION_KEY)
    ascending = [True, True]
    if sort_by != "configuration":
        columns.insert(0, sort_by)
        ascending.insert(0, sort_by != "ACC_pct")
    return result.sort_values(columns, ascending=ascending).reset_index(drop=True)


def configuration_summary(frame: pd.DataFrame) -> dict:
    """Best accuracy is None for no matches; leaders contains every tied key."""
    best = float(frame["ACC_pct"].max()) if len(frame) else None
    leaders = frame.loc[frame["ACC_pct"].eq(best), list(CONFIGURATION_KEY)]
    return {"configurations": len(frame), "best_ACC_pct": best,
            "leaders": list(leaders.sort_values(list(CONFIGURATION_KEY))
                            .itertuples(index=False, name=None))}


def accuracy_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Heatmap cells; absent combinations remain missing, never zero-filled."""
    return frame.pivot(index="framework", columns="model", values="ACC_pct")


def error_composition(frame: pd.DataFrame) -> pd.DataFrame:
    """Long-form chart data; preserve all four published percentage categories."""
    return frame.melt(id_vars=[*CONFIGURATION_KEY, "audit_instances"],
                      value_vars=list(RATE_COLUMNS), var_name="metric", value_name="rate_pct")


def compare_configurations(
    frame: pd.DataFrame, a: tuple[str, str], b: tuple[str, str],
) -> pd.DataFrame:
    """Compare two distinct keys from the passed (possibly filtered) population."""
    if a == b:
        raise ValueError("Select two distinct configurations.")
    values = []
    for key in (a, b):
        selected = frame.loc[frame["framework"].eq(key[0]) & frame["model"].eq(key[1])]
        if len(selected) != 1:
            raise ValueError(f"Expected one matching configuration for {key}.")
        values.append(selected.iloc[0][list(RATE_COLUMNS)].astype(float))
    return pd.DataFrame({"metric": RATE_COLUMNS, "A_pct": values[0].to_numpy(),
                         "B_pct": values[1].to_numpy(),
                         "delta_pp": (values[0] - values[1]).round(2).to_numpy()})


def evaluate_criteria(
    frame: pd.DataFrame, *, enabled: bool = True, min_acc: float = 0,
    max_ser: float = 100,
) -> pd.DataFrame:
    """Inclusive exploratory criteria, margins in pp, and explicit reasons.

    Disabled criteria produce nullable eligibility/margins, never a shortlist.
    Source rates and the caller's baseline comparison population stay unchanged.
    """
    for value in (min_acc, max_ser):
        if not isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Criteria must be finite percentages in [0, 100].")
    result = frame.copy()
    result["criteria_enabled"] = enabled
    result["min_ACC_pct"] = min_acc if enabled else pd.NA
    result["max_SER_pct"] = max_ser if enabled else pd.NA
    result["ACC_margin_pp"] = pd.Series(pd.NA, index=result.index, dtype="Float64")
    result["SER_margin_pp"] = pd.Series(pd.NA, index=result.index, dtype="Float64")
    result["eligible"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    result["criteria_reason"] = "Criteria disabled"
    if enabled:
        result["ACC_margin_pp"] = (result["ACC_pct"] - min_acc).round(2)
        result["SER_margin_pp"] = (max_ser - result["SER_pct"]).round(2)
        acc_ok, ser_ok = result["ACC_pct"].ge(min_acc), result["SER_pct"].le(max_ser)
        result["eligible"] = acc_ok & ser_ok
        result["criteria_reason"] = [
            "; ".join(reason for ok, reason in ((a, "ACC below minimum"),
                                               (s, "SER above maximum")) if not ok)
            or "Meets both criteria" for a, s in zip(acc_ok, ser_ok)
        ]
    return result


def filter_assertions(
    frame: pd.DataFrame, *, filing_years: Sequence[int] | None = None,
    forms: Sequence[str] | None = None, entity_ciks: Sequence[str] | None = None,
    assertion_types: Sequence[str] | None = None,
    assertion_codes: Sequence[str] | None = None,
    date_difference_only: bool = False, search: str = "",
) -> pd.DataFrame:
    """Scope only corpus fields; literal case-insensitive search ORs five fields.

    Use integer years and string CIKs/types, matching the prepared column types.
    Search whitespace is literal; the empty string imposes no search filter.
    """
    result = _filter(frame, {
        "report.filing-year_parsed": filing_years, "report.document-type": forms,
        "entity.cik": entity_ciks, "assertion.type": assertion_types,
        "assertion.code": assertion_codes,
    })
    if date_difference_only:
        result = result.loc[result["accepted_date_differs"]].copy()
    if search:
        matches = pd.Series(False, index=result.index)
        for column in SEARCH_COLUMNS:
            matches |= result[column].str.contains(search, case=False, regex=False, na=False)
        result = result.loc[matches].copy()
    return result


def assertion_summary(frame: pd.DataFrame) -> dict[str, int]:
    """Counts at distinct grains; date differences count assertion records."""
    return {"assertions": len(frame), "filings": frame["report.accession"].nunique(),
            "entities": frame["entity.cik"].nunique(), "rules": frame["assertion.code"].nunique(),
            "date_difference_records": int(frame["accepted_date_differs"].sum())}


def assertion_distribution(
    frame: pd.DataFrame, by: str = "assertion.type", *, top_n: int | None = None,
) -> pd.DataFrame:
    """Counts/shares by type or code, largest first, alphabetical ties.

    Shares always use ALL passed records, before top_n. Empty input returns an
    empty typed table. Missing groups, if present, are retained explicitly.
    """
    if by not in ("assertion.type", "assertion.code"):
        raise ValueError("Distribution must group by assertion type or code.")
    if top_n is not None and (not isinstance(top_n, int) or top_n < 1):
        raise ValueError("top_n must be a positive integer or None.")
    result = frame.groupby(by, dropna=False).size().rename("assertion_rows").reset_index()
    result["share_pct"] = result["assertion_rows"] / len(frame) * 100 if len(frame) else pd.Series(dtype=float)
    result = result.sort_values(["assertion_rows", by], ascending=[False, True])
    return result.head(top_n).reset_index(drop=True) if top_n else result.reset_index(drop=True)


def filing_distribution(frame: pd.DataFrame) -> pd.DataFrame:
    """Year/form assertion counts and distinct filings, chronologically sorted."""
    return frame.groupby(["report.filing-year_parsed", "report.document-type"],
                         dropna=False).agg(assertion_rows=("assertion.code", "size"),
                                          filings=("report.accession", "nunique")).reset_index()


def select_assertions(frame: pd.DataFrame, assertion_ids: Sequence[str]) -> pd.DataFrame:
    """Resolve detail/investigation IDs against a corpus, deduplicating selections.

    Pass the full corpus for a session investigation list, or the filtered corpus
    for current detail. Unknown/stale IDs raise rather than substitute a record.
    Output preserves requested order; no framework/configuration join is allowed.
    """
    ids = list(dict.fromkeys(assertion_ids))
    indexed = frame.set_index("assertion_id", drop=False)
    unknown = set(ids) - set(indexed.index)
    if unknown:
        raise ValueError(f"Unknown assertion IDs: {sorted(unknown)}")
    return indexed.loc[ids].reset_index(drop=True).copy()


def is_sec_url(value: str) -> bool:
    """Allow only http(s) sec.gov hosts/subdomains, without embedded credentials."""
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme in ("http", "https") and not parsed.username
                and not parsed.password and (host == "sec.gov" or host.endswith(".sec.gov")))
    except ValueError:
        return False


def export_csv(frame: pd.DataFrame) -> bytes:
    """Serialize the entire passed scope, including metadata, as UTF-8 CSV.

    Raw source strings and multiline evidence are preserved. Spreadsheet users
    should import identifier columns as text. This function does not write files.
    """
    return frame.to_csv(index=False, lineterminator="\n").encode("utf-8")


def reconciliation(
    corpus: pd.DataFrame | None = None, configurations: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Observed versus expected totals for supplied FULL sources, independently.

    This is a count report, not proof of hash/schema checks or notebook execution.
    Only successfully loaded sources should be supplied by the dashboard.
    """
    rows = []
    if corpus is not None:
        rows.extend((key, value, EXPECTED_CORPUS[key])
                    for key, value in assertion_summary(corpus).items())
    if configurations is not None:
        rows.append(("configurations", len(configurations), 20))
    result = pd.DataFrame(rows, columns=["measure", "observed", "expected"])
    result["matches"] = result["observed"].eq(result["expected"])
    return result
