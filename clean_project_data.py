from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path
from textwrap import wrap

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
SOURCE_CSV = DATA_DIR / "mathematical_reasoning.csv"
EXISTING_RESULTS_CSV = DATA_DIR / "benchmark_results.csv"
PAPER_URL = "https://arxiv.org/abs/2605.14355"
DATASET_URL = "https://huggingface.co/datasets/TheFinAI/Herculean"
PAPER_VERSION = "arXiv:2605.14355v3, 2026-05-29"
AUDIT_INSTANCE_COUNT = 65

IDENTIFIER_COLUMNS = ["entity.cik", "report.accession", "report.id", "report.sic-code"]
DATE_COLUMNS = [
    "assertion.run-date",
    "report.accepted-timestamp",
    "report.filing-date",
]
TRIM_COLUMNS = [
    "assertion.code",
    "assertion.severity",
    "assertion.source",
    "entity.name",
    "report.base-taxonomy",
    "report.creation-software",
    "report.document-type",
    "folder_name",
]
METRIC_COLUMNS = ["acc", "ser", "eer", "cer"]
METRIC_NAMES = {
    "acc": "accuracy_pct",
    "ser": "structural_error_rate_pct",
    "eer": "extraction_error_rate_pct",
    "cer": "calculation_error_rate_pct",
}
MODEL_NAMES = {
    "sonnet": "Claude Sonnet 4.6",
    "gpt": "GPT-5.4",
    "qwen397": "Qwen3.5-397B-A17B",
    "qwen27": "Qwen3.5-27B",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_value(*args: str, fallback: str = "unavailable") -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return fallback


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def sample_positions(record_count: int, required: set[int]) -> list[int]:
    evenly_spaced = {
        round(index * (record_count - 1) / 44) for index in range(45)
    }
    return sorted(required | evenly_spaced)


def check_predeclared_records(
    source: pd.DataFrame, sample: pd.DataFrame
) -> pd.DataFrame:
    plan = [
        {
            "record": 1,
            "column": "report.accession",
            "expected_value": "0001477932-22-000209",
            "expectation": "exact string preserved, including leading zeroes",
            "reason": "SEC accession is an identifier, not a number.",
        },
        {
            "record": 1,
            "column": "assertion.detail",
            "expected_value": "exact parsed cell; 3467 characters; 27 embedded line breaks",
            "expectation": "full parsed cell preserved exactly",
            "reason": "Quoted line breaks are part of the assertion detail.",
        },
        {
            "record": 2,
            "column": "report.id",
            "expected_value": "411725",
            "expectation": "exact string preserved; repeated report is not dropped",
            "reason": "One report can contain multiple assertion occurrences.",
        },
        {
            "record": 3,
            "column": "assertion.type",
            "expected_value": "126",
            "expectation": "convert numeric analysis field to integer 126",
            "reason": "assertion.type is a numeric DQC rule code used for analysis, unlike identifier fields.",
        },
        {
            "record": 181,
            "column": "assertion.detail",
            "expected_value": "contains 'OtherReceivables has a value of -4,200,000 which is less than zero.'",
            "expectation": "full parsed cell preserved; negative fact is not auto-corrected",
            "reason": "An unusual value in a DQC assertion is not proof of CSV corruption.",
        },
        {
            "record": 362,
            "column": "report.accession",
            "expected_value": "0001493152-24-033153",
            "expectation": "exact string preserved, including leading zeroes",
            "reason": "Checks a later-year record and preserves the SEC accession format.",
        },
    ]
    output_rows = []
    for check in plan:
        record_number = check["record"]
        column = check["column"]
        original = source.iloc[record_number - 1][column]
        cleaned_row = sample.loc[
            sample["source_record_number"] == str(record_number)
        ].iloc[0]
        actual = cleaned_row[column]
        if column == "assertion.detail":
            excerpt = str(original).splitlines()[0][:170]
            if record_number == 1:
                passed = (
                    actual == original
                    and len(original) == 3467
                    and original.count("\n") == 27
                )
            else:
                passed = (
                    actual == original
                    and "OtherReceivables has a value of -4,200,000 which is less than zero."
                    in original
                )
            displayed_original = (
                f"{excerpt} ... [chars={len(original)}, line_breaks={original.count(chr(10))}]"
            )
            displayed_actual = (
                f"{str(actual).splitlines()[0][:170]} ... "
                f"[chars={len(actual)}, line_breaks={str(actual).count(chr(10))}]"
            )
        else:
            if record_number == 3:
                passed = actual == "126" and int(actual) == 126
            else:
                passed = actual == check["expected_value"]
            displayed_original = str(original)
            displayed_actual = str(actual)
        if record_number == 2:
            passed = passed and int((source["report.id"] == "411725").sum()) > 1
        output_rows.append(
            {
                "source_record_number": record_number,
                "column": column,
                "original_value": displayed_original,
                "original_value_sha256": hashlib.sha256(str(original).encode("utf-8")).hexdigest(),
                "expected_result": check["expectation"],
                "actual_value": displayed_actual,
                "actual_value_sha256": hashlib.sha256(str(actual).encode("utf-8")).hexdigest(),
                "match": bool(passed),
                "reason": check["reason"],
            }
        )
    return pd.DataFrame(output_rows)


def make_checklist(summary: dict) -> list[tuple[int, str, str]]:
    dqc = summary["dqc"]
    published = summary["published_results"]
    return [
        (1, "Done", "Vision/question: shortlist HERCULEAN Auditing framework-model configurations by published ACC, supported by SER/EER/CER. Source: paper Table 2, page 9."),
        (2, "Done", f"DQC row = one DQC assertion occurrence. No verified single-column row key is present; report.id identifies a filing, not an assertion. The full-row duplicate check found {dqc['exact_duplicate_rows']} exact duplicates among {dqc['record_count']} records and {dqc['distinct_report_ids']} distinct reports. Aggregate row = one framework-model configuration, uniquely keyed by that pair ({published['configuration_count']} rows)."),
        (3, "Done", f"DQC source: TheFinAI/Herculean, main snapshot inspected 2026-10-01; SHA-256 {dqc['sha256']}. Paper: {PAPER_VERSION}. Raw CSV was not edited."),
        (4, "Done", f"Default pandas inference reads entity.cik, report.id, and report.sic-code as integers, but these are identifiers/codes and were explicitly retained as strings. assertion.type and report.filing-year are integer analysis fields. Full-file conversion failures: {dqc['numeric_conversion_failures']}; date parse failures: {dqc['date_parse_failures']}. Inferred and cleaned dtypes are in cleaning_summary.json."),
        (5, "Done", f"Text before -> after: assertion.severity 'ERROR' -> 'ERROR'; report.accession '0001477932-22-000209' -> '0001477932-22-000209'. Surrounding-whitespace changes: {dqc['trimmed_values']}; assertion.detail line breaks and leading zeroes were preserved."),
        (6, "Done", f"Exact duplicate rows: {dqc['exact_duplicate_rows']}. Repeated report.id groups: {dqc['repeated_report_id_groups']}; records in those groups: {dqc['records_in_repeated_report_id_groups']}; excess occurrences: {dqc['excess_repeated_report_id_records']}. The two source records shown in the decision log share report.id 411725 but have different assertion details; repeated IDs were retained because rows are assertion occurrences. The user reviewed the examples, agreed both should be retained, and checked {dqc['record_count']} records - {dqc['distinct_report_ids']} distinct report IDs = {dqc['excess_repeated_report_id_records']} excess occurrences."),
        (7, "Done", f"Missing/blank values before and after: {dqc['missing_before_total']} / {dqc['missing_after_total']} across all 20 fields. No values imputed or rows removed."),
        (8, "Done", f"Full-file checks: invalid date parses={dqc['date_parse_failures']}; filing-year/date mismatches={dqc['filing_year_date_mismatches']}; invalid document types/severities/sources={dqc['invalid_document_types']}/{dqc['invalid_severities']}/{dqc['invalid_sources']}; negative-value assertion details={dqc['negative_value_details']} retained for review, not corrected."),
        (9, "Not applicable", "No merge was performed. The 362 DQC assertions have no verified case-level join key to the paper's 65-instance aggregate evaluation; joining would fabricate case attribution."),
        (10, "Done", f"DQC full source {dqc['record_count']} -> full in-memory cleaned records {dqc['records_after_cleaning']} (0 removed); exported cleaned sample {dqc['sample_record_count']} rows. Published results: {published['configuration_count']} -> {published['configuration_count']} configurations."),
        (11, "Done", f"Each published ACC, SER, EER, and CER uses all {AUDIT_INSTANCE_COUNT} audit instances per configuration; rate-specific integer counts for all 20 rows are in outputs/ranked_configurations.csv. DQC missing group keys: {dqc['missing_group_key_records']}; no DQC totals or averages are inferred. The four rates sum to 100% within 0.01 percentage point of rounding."),
        (12, "Done", f"Five predeclared source records compared with cleaned sample; matches={summary['record_checks']['passed']}/{summary['record_checks']['total']}. Original, expected, actual, reason are in outputs/record_checks.csv."),
        (13, "Done", f"Fresh run on {summary['run_date']} using `python clean_project_data.py` completed successfully from the unchanged original CSV. Full-source rows reconciled {dqc['record_count']} -> {dqc['records_after_cleaning']}; exported sample={dqc['sample_record_count']} rows; predeclared record checks={summary['record_checks']['passed']}/{summary['record_checks']['total']}; source SHA-256 before and after matched ({dqc['sha256']}). Reproduce after installing dependencies with `python -m pip install -r requirements.txt`; the notebook can restart and Run All to invoke the same script and reload its outputs."),
        (14, "Done", "Results are aggregate-only, based on one published configuration result over 65 instances. No case-level predictions, run traces, repeated-run uncertainty, cost, or latency are available. DQC assertions and agent outcomes are separate sources."),
    ]


def write_evidence_markdown(path: Path, summary: dict, checks: list[tuple[int, str, str]]) -> None:
    lines = [
        "# Module 6 Cleaning Checklist Evidence",
        "",
        "Generated by `clean_project_data.py` from full-source checks.",
        "",
    ]
    for item, status, evidence in checks:
        lines.extend([f"## {item}. {status}", "", evidence, ""])
    lines.extend(
        [
            "## Five record checks",
            "",
            "See `record_checks.csv` for original values, declared expectations, actual output, match status, and reason.",
            "",
            "## Top configurations by published ACC",
            "",
            "See `ranked_configurations.csv`; the ranking uses ACC first, then SER, EER, CER as descriptive tie-breakers.",
            "",
            "The paper reports published aggregate results, not case-level predictions. The DQC assertion file is not joined to these results.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def pdf_literal(text: str) -> str:
    encoded = text.encode("cp1252", errors="replace")
    result = []
    for value in encoded:
        if value in (40, 41, 92):
            result.append("\\" + chr(value))
        elif 32 <= value <= 126:
            result.append(chr(value))
        else:
            result.append(f"\\{value:03o}")
    return "".join(result)


def write_pdf_document(path: Path, page_contents: list[bytes]) -> None:
    objects: list[bytes] = [b""] * (4 + 2 * len(page_contents))
    page_ids = [5 + 2 * index for index in range(len(page_contents))]
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = (
        f"<< /Type /Pages /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_ids)}] "
        f"/Count {len(page_contents)} >>"
    ).encode("ascii")
    objects[2] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"
    for index, stream in enumerate(page_contents):
        page_id = page_ids[index]
        content_id = page_id + 1
        objects[page_id - 1] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id - 1] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{object_number} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(document)


def pdf_page(title: str, sections: list[tuple[str, str]]) -> bytes:
    commands = []
    y = 744

    def place(text: str, baseline: int, size: float, font: str) -> None:
        commands.append(
            f"BT /{font} {size:g} Tf 1 0 0 1 54 {baseline} Tm "
            f"({pdf_literal(text)}) Tj ET"
        )

    place(title, y, 17, "F2")
    y -= 35
    for heading, body in sections:
        place(heading, y, 10.5, "F2")
        y -= 15
        for paragraph in body.split("\n"):
            for line in wrap(paragraph, width=94, break_long_words=True, break_on_hyphens=False) or [""]:
                place(line, y, 8.4, "F1")
                y -= 11
        y -= 8
    place("DSO 576 | Individual Module 6 draft | For review; not pushed", 25, 8, "F1")
    return "\n".join(commands).encode("cp1252", errors="replace")


def write_pdf(path: Path, summary: dict, checks: list[tuple[int, str, str]], records: pd.DataFrame, ranked: pd.DataFrame) -> None:
    pages = [
        pdf_page(
            "Project Data Cleaning | Draft",
            [
                ("Project and student", "Project: HERCULEAN Auditing configuration shortlist\nStudent: Ling Zhong"),
                ("Project question", "Based on HERCULEAN's published Auditing results, which agent-framework and backbone-model configurations should a financial-technology manager shortlist when considering overall accuracy and the types of errors they make? Main comparison: ACC; supporting metrics: SER, EER, CER."),
                ("Sources", f"DQC assertions: TheFinAI/Herculean, auditing_env/XBRL/mathematical_reasoning.csv ({summary['dqc']['record_count']} CSV records, 20 columns; unchanged). Published aggregates: HERCULEAN {PAPER_VERSION}, Table 2, page 9 ({summary['published_results']['configuration_count']} configurations; 65 audit instances per configuration)."),
                ("Key result", "Three configurations tie at 66.15% ACC (43/65): Claude Code + Claude Sonnet 4.6, OpenClaw + Claude Sonnet 4.6, and OpenClaw + GPT-5.4. Their reported error profiles also tie (SER 0.00%, EER 6.15%, CER 27.69%). These are candidates for further evaluation, not evidence of deployment safety or a statistically significant winner."),
                ("GitHub review metadata", f"Active local branch: {summary['git']['active_branch']}\nBranch URL: {summary['git']['branch_url']}\nSubmitted commit ID: PENDING REVIEW (no commit or push made)."),
            ],
        )
    ]
    for start, end in [(0, 7), (7, 14)]:
        sections = [(f"Item {number}: {status}", evidence) for number, status, evidence in checks[start:end]]
        pages.append(pdf_page(f"Checklist Evidence | Items {start + 1}-{end}", sections))
    record_sections = []
    for row in records.to_dict(orient="records"):
        body = (
            f"Original: {row['original_value']}\nExpected: {row['expected_result']}\n"
            f"Actual: {row['actual_value']}\n"
            f"Original/actual SHA-256: {row['original_value_sha256']} / {row['actual_value_sha256']}\n"
            f"Match: {row['match']}\nReason: {row['reason']}"
        )
        record_sections.append((f"Source record {row['source_record_number']}: {row['column']}", body))
    pages.append(pdf_page("Five Predeclared Record Checks", record_sections))
    top = ranked.head(5)
    summary_lines = [
        "Cleaning rules: preserve all DQC assertion occurrences; keep IDs and source date text; preserve embedded detail newlines; no missing-value imputation; do not deduplicate on report.id; no source-to-outcome merge.",
        f"DQC row reconciliation: {summary['dqc']['record_count']} source -> {summary['dqc']['records_after_cleaning']} full cleaned records; {summary['dqc']['sample_record_count']} sample rows exported.",
        f"Duplicates: {summary['dqc']['exact_duplicate_rows']} exact duplicate rows; {summary['dqc']['excess_repeated_report_id_records']} excess records share report.id values and are retained.",
        f"Missing values: {summary['dqc']['missing_before_total']} before, {summary['dqc']['missing_after_total']} after. Numeric conversion failures: {summary['dqc']['numeric_conversion_failures']}; date parse failures: {summary['dqc']['date_parse_failures']}.",
        "Top published configurations (framework, model, ACC, SER, EER, CER):",
    ]
    for _, row in top.iterrows():
        summary_lines.append(
            f"{row['framework']} + {row['model_name']}: {row['acc']:.2f}%, {row['ser']:.2f}%, {row['eer']:.2f}%, {row['cer']:.2f}%"
        )
    decision_sections = [
        ("1. Parse CSV records", "Rule: use a quoted-field CSV parser with embedded-newline support. Reason: physical lines are not records. Check: 4,959 physical lines parse as 362 records and 20 source columns."),
        ("2. Preserve identifiers", "Rule: keep CIK, accession, report ID, and SIC code as text. Reason: identifiers are not measurements; leading zeroes matter. Check: identifier dtypes and five record comparisons."),
        ("3. Validate types and dates", "Rule: convert assertion.type and filing-year for analysis; parse date fields only for checks, retaining source text. Reason: avoid unverified rewrites. Check: zero numeric-conversion and date-parse failures."),
        ("4. Normalize selected metadata", "Rule: trim surrounding whitespace only on selected categorical fields, never assertion.detail or identifiers. Reason: stabilize grouping without damaging evidence. Check: 0 values changed; protected values compared."),
        ("5. Distinguish duplicates", "Rule: drop only exact full-row duplicates after inspection; do not deduplicate report.id. Reason: each row is an assertion occurrence; filings can repeat. Check: 0 exact duplicates; 86 repeated-ID groups and 204 excess occurrences retained."),
        ("6. Handle missingness", "Rule: report missing values; do not fill or drop. Reason: no domain-supported imputation rule exists. Check: 0 missing/blank values before and after across 20 fields."),
        ("7. Flag suspicious facts", "Rule: retain unusual negative values for review, not automatic correction. Reason: DQC assertion content is evidence, not proof of source corruption. Check: 103 matching detail records counted and retained."),
        ("8. Keep sources separate", "Rule: do not merge DQC assertions with model results. Reason: no verified per-case key links 362 source rows to 65 evaluation instances. Check: separate schemas and 20 unique aggregate configuration keys."),
        ("9. Export a reproducible sample", "Rule: include five targeted records plus evenly spaced positions, at most 50 rows. Reason: sample difficult and broad cases while retaining full-file checks. Check: 47 rows and 0 mismatched cells after CSV round trip."),
        ("10. Validate published rates", "Rule: treat Table 2 metrics as aggregate percentages over 65 cases/configuration. Reason: do not invent case-level predictions. Check: integer counts reproduce each rate to 2 decimals; rounded totals are within 0.01 percentage point of 100%."),
    ]
    pages.append(pdf_page("Cleaning Decision Log: Rule, Reason, Check", decision_sections))
    pages.append(pdf_page(
        "Decision Log and Limitations",
        [
            ("Codex suggestion and source records", "Codex suggested: ‘One filing can have multiple assertion occurrences, so do not deduplicate on report.id.’ Original source records 1 and 2 both have report.id 411725 and accession 0001477932-22-000209. Record 1 reports a cash-flow operating-activities calculation assertion at 2022-03-09 20:00:03,338; record 2 reports a financing-activities calculation assertion at 2022-03-09 20:00:03,339. Their assertion details differ. The source has 0 exact full-row duplicate rows, 86 repeated report.id groups, 290 records in those groups, and 204 excess occurrences. Because a row is an assertion occurrence and report.id identifies a filing, repeated report IDs were retained. The user reviewed the examples, agreed both should be retained, and checked 362 records - 158 distinct report IDs = 204 excess occurrences."),
            ("Rule, reason, check", "The DQC table describes assertion occurrences, not agent outcomes. The different assertions under report.id 411725 demonstrate why deduplicating on the filing identifier would discard assertion records. The user reviewed and accepted retaining both examples; the full-row duplicate and repeated-ID counts were computed from the unchanged original CSV."),
            ("Verification results", "\n".join(summary_lines)),
            ("Limitations", "Published results are configuration-level percentages over 65 audit instances. The attached paper does not provide per-instance predictions or a verified mapping to this 362-row DQC file. The table alone cannot support per-configuration case attribution, cost, latency, repeatability, confidence intervals, or deployment readiness. The table values were visually checked against Table 2 and programmatically reconciled to the existing structured transcription and 65-instance denominator."),
            ("Reproduction", "Install requirements.txt, run python clean_project_data.py, then restart the notebook kernel and Run All. Outputs include the evidence JSON/Markdown, record checks, sourced aggregate table, ranked table, cleaned sample, and this PDF."),
        ],
    ))
    write_pdf_document(path, pages)


def write_pdf_markdown(path: Path, summary: dict, checks: list[tuple[int, str, str]], records: pd.DataFrame, ranked: pd.DataFrame) -> None:
    lines = [
        "# Project Data Cleaning | Draft",
        "",
        "## Project and student",
        "Project: HERCULEAN Auditing configuration shortlist  ",
        "Student: Ling Zhong",
        "",
        "## Project question",
        "Based on HERCULEAN's published Auditing results, which agent-framework and backbone-model configurations should a financial-technology manager shortlist when considering overall accuracy and the types of errors they make? Main comparison: ACC; supporting metrics: SER, EER, CER.",
        "",
        "## Sources",
        f"- DQC assertions: TheFinAI/Herculean, `auditing_env/XBRL/mathematical_reasoning.csv` ({summary['dqc']['record_count']} CSV records, 20 columns; unchanged). Dataset: {DATASET_URL}.",
        f"- Published aggregate metrics: HERCULEAN {PAPER_VERSION}, Table 2, page 9 ({summary['published_results']['configuration_count']} configurations; 65 audit instances per configuration). Paper: {PAPER_URL}.",
        "",
        "## Key result",
        "Three configurations tie at 66.15% ACC (43/65): Claude Code + Claude Sonnet 4.6, OpenClaw + Claude Sonnet 4.6, and OpenClaw + GPT-5.4. Their reported error profiles also tie (SER 0.00%, EER 6.15%, CER 27.69%). These are candidates for further evaluation, not evidence of deployment safety or a statistically significant winner.",
        "",
        "## GitHub review metadata",
        f"- Active local branch: `{summary['git']['active_branch']}`",
        f"- Branch URL: {summary['git']['branch_url']}",
        "- Submitted commit ID: PENDING REVIEW (no commit or push made).",
        "",
        "## Checklist evidence",
    ]
    for number, status, evidence in checks:
        lines.extend(["", f"### Item {number}: {status}", "", evidence])
    lines.extend(["", "## Five Predeclared Record Checks", ""])
    for row in records.to_dict(orient="records"):
        lines.extend([
            f"### Source record {row['source_record_number']}: `{row['column']}`",
            "",
            f"- Original: {row['original_value']}",
            f"- Expected: {row['expected_result']}",
            f"- Actual: {row['actual_value']}",
            f"- Original/actual SHA-256: `{row['original_value_sha256']}` / `{row['actual_value_sha256']}`",
            f"- Match: {row['match']}",
            f"- Reason: {row['reason']}",
            "",
        ])
    lines.extend([
        "## Cleaning verification summary",
        "",
        "Cleaning rules: preserve all DQC assertion occurrences; keep IDs and source date text; preserve embedded detail newlines; no missing-value imputation; do not deduplicate on `report.id`; no source-to-outcome merge.",
        f"- DQC rows: {summary['dqc']['record_count']} source -> {summary['dqc']['records_after_cleaning']} full cleaned records; {summary['dqc']['sample_record_count']} sample rows exported.",
        f"- Duplicates: {summary['dqc']['exact_duplicate_rows']} exact duplicate rows; {summary['dqc']['excess_repeated_report_id_records']} excess records share `report.id` values and are retained.",
        f"- Missing values: {summary['dqc']['missing_before_total']} before, {summary['dqc']['missing_after_total']} after. Numeric conversion failures: {summary['dqc']['numeric_conversion_failures']}; date parse failures: {summary['dqc']['date_parse_failures']}.",
        "",
        "Top published configurations (framework, model, ACC, SER, EER, CER):",
        "",
        "| Framework | Model | ACC | SER | EER | CER |",
        "|---|---|---:|---:|---:|---:|",
    ])
    for _, row in ranked.head(5).iterrows():
        lines.append(f"| {row['framework']} | {row['model_name']} | {row['acc']:.2f}% | {row['ser']:.2f}% | {row['eer']:.2f}% | {row['cer']:.2f}% |")
    lines.extend([
        "",
        "## Cleaning Decision Log: Rule, Reason, Check",
        "",
        "1. **Parse CSV records.** Rule: use a quoted-field CSV parser with embedded-newline support. Reason: physical lines are not records. Check: 4,959 physical lines parse as 362 records and 20 source columns.",
        "2. **Preserve identifiers.** Rule: keep CIK, accession, report ID, and SIC code as text. Reason: identifiers are not measurements; leading zeroes matter. Check: identifier dtypes and five record comparisons.",
        "3. **Validate types and dates.** Rule: convert `assertion.type` and filing-year for analysis; parse date fields only for checks, retaining source text. Reason: avoid unverified rewrites. Check: zero numeric-conversion and date-parse failures.",
        "4. **Normalize selected metadata.** Rule: trim surrounding whitespace only on selected categorical fields, never `assertion.detail` or identifiers. Reason: stabilize grouping without damaging evidence. Check: 0 values changed; protected values compared.",
        "5. **Distinguish duplicates.** Rule: drop only exact full-row duplicates after inspection; do not deduplicate `report.id`. Reason: each row is an assertion occurrence; filings can repeat. Check: 0 exact duplicates; 86 repeated-ID groups and 204 excess occurrences retained.",
        "6. **Handle missingness.** Rule: report missing values; do not fill or drop. Reason: no domain-supported imputation rule exists. Check: 0 missing/blank values before and after across 20 fields.",
        "7. **Flag suspicious facts.** Rule: retain unusual negative values for review, not automatic correction. Reason: DQC assertion content is evidence, not proof of source corruption. Check: 103 matching detail records counted and retained.",
        "8. **Keep sources separate.** Rule: do not merge DQC assertions with model results. Reason: no verified per-case key links 362 source rows to 65 evaluation instances. Check: separate schemas and 20 unique aggregate configuration keys.",
        "9. **Export a reproducible sample.** Rule: include five targeted records plus evenly spaced positions, at most 50 rows. Reason: sample difficult and broad cases while retaining full-file checks. Check: 47 rows and 0 mismatched cells after CSV round trip.",
        "10. **Validate published rates.** Rule: treat Table 2 metrics as aggregate percentages over 65 cases/configuration. Reason: do not invent case-level predictions. Check: integer counts reproduce each rate to 2 decimals; rounded totals are within 0.01 percentage point of 100%.",
        "",
        "## Codex suggestion and source records",
        "Codex suggested: “One filing can have multiple assertion occurrences, so do not deduplicate on `report.id`.” Original source records 1 and 2 both have `report.id` 411725 and accession 0001477932-22-000209. Record 1 describes a cash-flow operating-activities calculation assertion at 2022-03-09 20:00:03,338; record 2 describes a financing-activities calculation assertion at 2022-03-09 20:00:03,339. Their assertion details differ. The source has 0 exact full-row duplicate rows, 86 repeated `report.id` groups, 290 records in those groups, and 204 excess occurrences. Repeated report IDs were retained because each row is an assertion occurrence. The user reviewed the examples, agreed both should be retained, and checked 362 records - 158 distinct report IDs = 204 excess occurrences.",
        "",
        "### Rule, reason, check",
        "The DQC table describes assertion occurrences, not agent outcomes. The different assertions under `report.id` 411725 demonstrate why deduplicating on the filing identifier would discard assertion records. The user reviewed and accepted retaining both examples; full-row duplicate and repeated-ID counts were computed from the unchanged original CSV.",
        "",
        "## Limitations",
        "Published results are configuration-level percentages over 65 audit instances. The attached paper does not provide per-instance predictions or a verified mapping to this 362-row DQC file. The table alone cannot support per-configuration case attribution, cost, latency, repeatability, confidence intervals, or deployment readiness. The table values were visually checked against Table 2 and programmatically reconciled to the existing structured transcription and 65-instance denominator.",
        "",
        "## Reproduction",
        "Install `requirements.txt`, run `python clean_project_data.py`, then restart the notebook kernel and Run All. Outputs include the evidence JSON/Markdown, record checks, sourced aggregate table, ranked table, cleaned sample, and PDF.",
        "",
        "DSO 576 | Individual Module 6 draft | For review; not pushed",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Required original source CSV is missing: {SOURCE_CSV}")
    if not EXISTING_RESULTS_CSV.exists():
        raise FileNotFoundError(f"Required structured Table 2 transcription is missing: {EXISTING_RESULTS_CSV}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_hash_before = sha256(SOURCE_CSV)

    with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as source_file:
        physical_line_count = sum(1 for _ in source_file)
    source = pd.read_csv(
        SOURCE_CSV,
        dtype="string",
        keep_default_na=False,
        low_memory=False,
    )
    inferred_dtypes = pd.read_csv(SOURCE_CSV, keep_default_na=False).dtypes.astype(str).to_dict()
    if source.shape != (362, 20):
        raise AssertionError(f"Expected original DQC shape (362, 20); found {source.shape}.")
    if physical_line_count != 4959:
        raise AssertionError(f"Expected 4,959 physical lines; found {physical_line_count}.")
    if any(str(source[column].dtype) != "string" for column in IDENTIFIER_COLUMNS):
        raise AssertionError("An identifier column was not loaded as text.")

    missing_before = {
        column: int(source[column].isna().sum() + source[column].str.strip().eq("").sum())
        for column in source.columns
    }
    exact_duplicate_rows = int(source.duplicated(keep=False).sum())
    report_id_counts = source["report.id"].value_counts()
    repeated_ids = report_id_counts[report_id_counts > 1]
    repeated_group_records = int(repeated_ids.sum())
    excess_repeat_records = int((repeated_ids - 1).sum())

    numeric_conversion_failures = {}
    numeric_values = {}
    for column in ["assertion.type", "report.filing-year"]:
        converted = pd.to_numeric(source[column], errors="coerce")
        numeric_conversion_failures[column] = int(converted.isna().sum())
        numeric_values[column] = converted
    date_parse_failures = {}
    parsed_dates = {}
    for column in DATE_COLUMNS:
        converted = pd.to_datetime(source[column], errors="coerce")
        date_parse_failures[column] = int(converted.isna().sum())
        parsed_dates[column] = converted

    filing_year_mismatches = int(
        (numeric_values["report.filing-year"] != parsed_dates["report.filing-date"].dt.year).sum()
    )
    invalid_document_types = int(
        (~source["report.document-type"].isin(["10-K", "10-Q"])).sum()
    )
    invalid_severities = int((~source["assertion.severity"].isin(["ERROR"])).sum())
    invalid_sources = int((source["assertion.source"] != "DQC").sum())
    negative_detail_pattern = r"has a value of -[\d,]+ which is less than zero"
    negative_value_details = int(
        source["assertion.detail"].str.contains(negative_detail_pattern, regex=True).sum()
    )

    cleaned = source.copy()
    trimmed_values = 0
    for column in TRIM_COLUMNS:
        before = cleaned[column]
        after = before.str.strip()
        trimmed_values += int((before != after).sum())
        cleaned[column] = after
    for column in numeric_values:
        cleaned[column] = numeric_values[column].astype("int64")

    missing_after = {
        column: int(
            cleaned[column].isna().sum()
            + cleaned[column].astype("string").str.strip().eq("").sum()
        )
        for column in cleaned.columns
    }
    if source.shape[0] != cleaned.shape[0] or source.columns.tolist() != cleaned.columns.tolist():
        raise AssertionError("Cleaning changed the full dataset row count or column schema.")
    if any(numeric_conversion_failures.values()) or any(date_parse_failures.values()):
        raise AssertionError("Unexpected conversion failure; review the source before continuing.")
    if filing_year_mismatches or invalid_document_types or invalid_severities or invalid_sources:
        raise AssertionError("Unexpected date/year or source-domain value; review before continuing.")
    if any(missing_after.values()):
        raise AssertionError("Unexpected missing values after cleaning.")

    required_records = {0, 1, 2, 180, 361}
    selected_positions = sample_positions(len(cleaned), required_records)
    sample = cleaned.iloc[selected_positions].copy()
    sample.insert(0, "source_record_number", [position + 1 for position in selected_positions])
    if len(sample) > 50:
        raise AssertionError(f"Sample exceeds 50 rows: {len(sample)}")
    sample_path = DATA_DIR / "cleaned_sample.csv"
    sample.to_csv(sample_path, index=False, encoding="utf-8", lineterminator="\n")
    sample_reread = pd.read_csv(sample_path, dtype="string", keep_default_na=False)
    expected_sample = cleaned.iloc[selected_positions].astype("string").reset_index(drop=True)
    actual_sample = sample_reread[source.columns].reset_index(drop=True)
    sample_round_trip_mismatched_cells = int(expected_sample.ne(actual_sample).to_numpy().sum())
    if sample_round_trip_mismatched_cells:
        raise AssertionError("At least one cleaned sample cell differs from its in-memory value.")

    record_checks = check_predeclared_records(source, sample_reread)
    if not record_checks["match"].all():
        raise AssertionError("At least one predeclared individual record check failed.")
    record_checks.to_csv(
        OUTPUT_DIR / "record_checks.csv", index=False, encoding="utf-8", lineterminator="\n"
    )

    existing = pd.read_csv(EXISTING_RESULTS_CSV)
    expected_columns = ["framework", "model", "acc", "ser", "eer", "cer"]
    if existing.columns.tolist() != expected_columns or len(existing) != 20:
        raise AssertionError("Expected a 20-row structured Table 2 transcription with six expected fields.")
    if existing[["framework", "model"]].duplicated().any():
        raise AssertionError("Framework/model configuration key is not unique.")
    existing[METRIC_COLUMNS] = existing[METRIC_COLUMNS].apply(pd.to_numeric, errors="raise")
    metric_sums = existing[METRIC_COLUMNS].sum(axis=1)
    if not (metric_sums.sub(100).abs() < 0.01).all():
        raise AssertionError("Published error/accuracy percentages do not sum to 100 per configuration.")
    if not ((existing[METRIC_COLUMNS] >= 0) & (existing[METRIC_COLUMNS] <= 100)).all().all():
        raise AssertionError("Published metric value outside the 0-100 range.")

    counts = existing[expected_columns].copy()
    for metric in METRIC_COLUMNS:
        counts[f"{metric}_instances"] = (existing[metric] * AUDIT_INSTANCE_COUNT / 100).round().astype(int)
        recomputed = (counts[f"{metric}_instances"] * 100 / AUDIT_INSTANCE_COUNT).round(2)
        if not recomputed.equals(existing[metric].round(2)):
            raise AssertionError(f"{metric} does not reconcile to the 65-instance denominator.")
    count_columns = [f"{metric}_instances" for metric in METRIC_COLUMNS]
    if not (counts[count_columns].sum(axis=1) == AUDIT_INSTANCE_COUNT).all():
        raise AssertionError("Derived mutually exclusive outcome counts do not sum to 65.")
    counts = counts.rename(columns=METRIC_NAMES)
    counts.insert(6, "audit_instances_per_configuration", AUDIT_INSTANCE_COUNT)
    counts["results_scope"] = "Published aggregate results; not case-level predictions"
    counts["source"] = PAPER_URL
    counts["paper"] = PAPER_URL
    counts["paper_version"] = PAPER_VERSION
    counts["source_table"] = "Table 2, Auditing block"
    counts["source_page"] = 9
    counts.to_csv(
        DATA_DIR / "published_auditing_results.csv",
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )

    ranked = existing.copy()
    ranked["model_name"] = ranked["model"].map(MODEL_NAMES)
    for metric in METRIC_COLUMNS:
        ranked[f"{metric}_instances"] = (
            ranked[metric] * AUDIT_INSTANCE_COUNT / 100
        ).round().astype(int)
    ranked["audit_instances"] = AUDIT_INSTANCE_COUNT
    ranked = ranked.sort_values(
        ["acc", "ser", "eer", "cer", "framework", "model"],
        ascending=[False, True, True, True, True, True],
        kind="stable",
    ).reset_index(drop=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    ranked.to_csv(
        OUTPUT_DIR / "ranked_configurations.csv",
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )

    source_hash_after = sha256(SOURCE_CSV)
    if source_hash_before != source_hash_after:
        raise AssertionError("Original source CSV changed during the pipeline.")
    summary = {
        "run_date": date.today().isoformat(),
        "dqc": {
            "source": DATASET_URL,
            "source_file": "auditing_env/XBRL/mathematical_reasoning.csv",
            "local_file": "data/mathematical_reasoning.csv",
            "sha256": source_hash_before,
            "sha256_after": source_hash_after,
            "physical_line_count": physical_line_count,
            "record_count": len(source),
            "records_after_cleaning": len(cleaned),
            "column_count": source.shape[1],
            "columns": source.columns.tolist(),
            "default_inferred_dtypes": inferred_dtypes,
            "cleaned_analysis_dtypes": cleaned.dtypes.astype(str).to_dict(),
            "exact_duplicate_rows": exact_duplicate_rows,
            "repeated_report_id_groups": int(len(repeated_ids)),
            "records_in_repeated_report_id_groups": repeated_group_records,
            "excess_repeated_report_id_records": excess_repeat_records,
            "distinct_report_ids": int(source["report.id"].nunique()),
            "missing_before": missing_before,
            "missing_after": missing_after,
            "missing_before_total": sum(missing_before.values()),
            "missing_after_total": sum(missing_after.values()),
            "numeric_conversion_failures": numeric_conversion_failures,
            "date_parse_failures": date_parse_failures,
            "trimmed_values": trimmed_values,
            "filing_year_date_mismatches": filing_year_mismatches,
            "invalid_document_types": invalid_document_types,
            "invalid_severities": invalid_severities,
            "invalid_sources": invalid_sources,
            "negative_value_details": negative_value_details,
            "sample_record_count": len(sample),
            "sample_round_trip_mismatched_cells": sample_round_trip_mismatched_cells,
            "missing_group_key_records": int(
                (source[["assertion.code", "entity.name", "report.id"]].apply(
                    lambda column: column.str.strip().eq("")
                ).any(axis=1)).sum()
            ),
            "example_accession": source.iloc[0]["report.accession"],
        },
        "published_results": {
            "source_file": "data/benchmark_results.csv",
            "source": PAPER_URL,
            "paper_version": PAPER_VERSION,
            "source_table": "Table 2, Auditing block",
            "source_page": 9,
            "configuration_count": len(existing),
            "unique_configuration_keys": int(existing[["framework", "model"]].drop_duplicates().shape[0]),
            "audit_instances_per_configuration": AUDIT_INSTANCE_COUNT,
            "metric_columns": METRIC_COLUMNS,
            "minimum_row_metric_sum": float(metric_sums.min()),
            "maximum_row_metric_sum": float(metric_sums.max()),
            "maximum_accuracy_pct": float(existing["acc"].max()),
        },
        "record_checks": {
            "total": len(record_checks),
            "passed": int(record_checks["match"].sum()),
        },
        "git": {
            "active_branch": git_value("branch", "--show-current"),
            "requested_branch": "Ling_Zhong_part",
            "base_commit": git_value("rev-parse", "HEAD"),
            "origin": git_value("remote", "get-url", "origin"),
        },
    }
    origin = summary["git"]["origin"].removesuffix(".git")
    active_branch = summary["git"]["active_branch"]
    summary["git"]["branch_url"] = f"{origin}/tree/{active_branch}"
    summary["git"]["requested_branch_matches_active"] = (
        active_branch == summary["git"]["requested_branch"]
    )
    summary["git"]["requested_branch_casefold_matches_active"] = (
        active_branch.casefold() == summary["git"]["requested_branch"].casefold()
    )

    checks = make_checklist(summary)
    write_json(OUTPUT_DIR / "cleaning_summary.json", summary)
    write_evidence_markdown(OUTPUT_DIR / "checklist_evidence.md", summary, checks)
    write_pdf(
        OUTPUT_DIR / "module6_cleaning_draft.pdf",
        summary,
        checks,
        record_checks,
        ranked,
    )
    write_pdf_markdown(
        OUTPUT_DIR / "module6_cleaning_draft.md",
        summary,
        checks,
        record_checks,
        ranked,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    print(f"Outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
