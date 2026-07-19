from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re


ROOT = Path(__file__).resolve().parent

WORKFLOW_DIR = ROOT / ".github" / "workflows"

CHECK_DIRS = [
    ROOT / "fast",
    ROOT / "guides",
    ROOT / "xtream-epg",
]

REPORT = ROOT / "repo_audit_report.txt"


def relative(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")


def read_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return ""


def get_checked_files():
    files = []

    for directory in CHECK_DIRS:
        if not directory.exists():
            continue

        for path in directory.rglob("*"):
            if path.is_file():
                files.append(path)

    return files


def get_workflows():
    if not WORKFLOW_DIR.exists():
        return []

    return sorted(
        [
            path
            for path in WORKFLOW_DIR.rglob("*")
            if path.is_file()
            and path.suffix.lower() in {".yml", ".yaml"}
        ]
    )


def normalize(value):
    return value.replace("\\", "/").strip()


def find_references(workflow_text, files):
    referenced = set()

    file_lookup = {
        relative(path): path
        for path in files
    }

    basename_lookup = defaultdict(list)

    for path in files:
        basename_lookup[path.name].append(path)

    for file_path, actual_path in file_lookup.items():

        if re.search(
            rf"(?<![A-Za-z0-9_.-])"
            rf"{re.escape(file_path)}"
            rf"(?![A-Za-z0-9_.-])",
            workflow_text
        ):
            referenced.add(actual_path)

    for path in files:

        if path.name not in workflow_text:
            continue

        matches = basename_lookup[path.name]

        if len(matches) == 1:
            referenced.add(matches[0])

    return referenced


def classify(path):
    suffix = path.suffix.lower()

    if suffix in {".xml", ".gz"}:
        return "Guides / Generated Data"

    if suffix in {".py", ".js", ".ts", ".sh"}:
        return "Scripts"

    if suffix in {".txt", ".json", ".csv"}:
        return "Data / Configuration"

    return "Other"


def main():

    checked_files = get_checked_files()
    workflows = get_workflows()

    referenced_files = set()
    workflow_references = {}

    for workflow in workflows:

        workflow_text = read_text(workflow)

        references = find_references(
            workflow_text,
            checked_files
        )

        workflow_references[workflow] = references
        referenced_files.update(references)

    unreferenced_files = set(checked_files) - referenced_files

    used_by_category = defaultdict(list)
    unused_by_category = defaultdict(list)

    for path in sorted(
        referenced_files,
        key=lambda item: relative(item).lower()
    ):
        used_by_category[
            classify(path)
        ].append(relative(path))

    for path in sorted(
        unreferenced_files,
        key=lambda item: relative(item).lower()
    ):
        unused_by_category[
            classify(path)
        ].append(relative(path))

    lines = []

    lines.append(
        "REPOSITORY WORKFLOW DEPENDENCY AUDIT"
    )
    lines.append(
        "===================================="
    )
    lines.append("")

    lines.append(
        f"Generated: {datetime.utcnow().isoformat()} UTC"
    )
    lines.append("")

    lines.append(
        "AUDIT SCOPE"
    )
    lines.append(
        "-----------"
    )
    lines.append(
        ".github/workflows/"
    )
    lines.append(
        "fast/"
    )
    lines.append(
        "guides/"
    )
    lines.append(
        "xtream-epg/"
    )
    lines.append("")

    lines.append(
        "SUMMARY"
    )
    lines.append(
        "-------"
    )
    lines.append(
        f"Workflows analyzed: {len(workflows)}"
    )
    lines.append(
        f"Files checked: {len(checked_files)}"
    )
    lines.append(
        f"Files referenced by workflows: {len(referenced_files)}"
    )
    lines.append(
        f"Files not referenced by workflows: {len(unreferenced_files)}"
    )
    lines.append("")

    lines.append(
        "FILES REFERENCED BY WORKFLOWS"
    )
    lines.append(
        "============================="
    )
    lines.append("")

    for category in sorted(used_by_category):

        lines.append(category)
        lines.append("-" * len(category))

        for item in used_by_category[category]:
            lines.append(item)

        lines.append("")

    lines.append(
        "FILES NOT REFERENCED BY ANY WORKFLOW"
    )
    lines.append(
        "===================================="
    )
    lines.append("")

    if not unreferenced_files:

        lines.append(
            "No unreferenced files found."
        )

    else:

        for category in sorted(unused_by_category):

            items = unused_by_category[category]

            lines.append(
                f"{category}: {len(items)} files"
            )

            for item in items:
                lines.append(
                    f"  {item}"
                )

            lines.append("")

    lines.append(
        "WORKFLOW DEPENDENCY SUMMARY"
    )
    lines.append(
        "==========================="
    )
    lines.append("")

    for workflow in workflows:

        references = workflow_references[workflow]

        lines.append(
            relative(workflow)
        )

        if not references:

            lines.append(
                "  No files found in audit scope"
            )

        else:

            for path in sorted(
                references,
                key=lambda item: relative(item).lower()
            ):
                lines.append(
                    f"  - {relative(path)}"
                )

        lines.append("")

    lines.append(
        "IMPORTANT"
    )
    lines.append(
        "========="
    )
    lines.append("")
    lines.append(
        "This audit does not delete or modify any files."
    )
    lines.append(
        "Files outside the audit scope were ignored."
    )
    lines.append(
        "The logos directory was ignored."
    )

    report = "\n".join(lines) + "\n"

    REPORT.write_text(
        report,
        encoding="utf-8"
    )

    print(report)


if __name__ == "__main__":
    main()
