#!/usr/bin/env python3

import os
import re
import json
import gzip
from pathlib import Path
from datetime import datetime


ROOT = Path.cwd()

OUTPUT_TXT = ROOT / "repo_audit_report.txt"
OUTPUT_JSON = ROOT / "repo_audit.json"


IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
}


TEXT_EXTENSIONS = {
    ".yml",
    ".yaml",
    ".py",
    ".js",
    ".sh",
    ".txt",
    ".json",
    ".xml",
    ".md",
}


def scan_files():

    files = []

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        if any(part in IGNORE_DIRS for part in path.parts):
            continue

        files.append(path)

    return files



def read_text(path):

    try:

        if path.suffix == ".gz":

            with gzip.open(path, "rt", errors="ignore") as f:
                return f.read()

        return path.read_text(
            errors="ignore"
        )

    except Exception:

        return ""



def get_age(path):

    try:

        modified = datetime.fromtimestamp(
            path.stat().st_mtime
        )

        days = (
            datetime.now() - modified
        ).days

        return days

    except Exception:

        return None



def find_workflows(files):

    workflows = []

    for f in files:

        if ".github" not in str(f):
            continue

        if f.suffix not in {".yml",".yaml"}:
            continue

        text = read_text(f)

        workflows.append({

            "file": str(f.relative_to(ROOT)),
            "name": extract_name(text),
            "references": find_paths(text),
            "secrets": find_secrets(text)

        })

    return workflows



def extract_name(text):

    match = re.search(
        r"name:\s*(.+)",
        text
    )

    if match:
        return match.group(1).strip()

    return "Unknown"



def find_paths(text):

    found = set()

    patterns = [

        r"[\w./-]+\.(?:py|js|sh|xml|txt|json)",
        r"scripts/[\w./-]+",
        r"guides/[\w./-]+"

    ]

    for pattern in patterns:

        for match in re.findall(pattern,text):

            found.add(match)

    return sorted(found)



def find_secrets(text):

    return sorted(
        set(
            re.findall(
                r"secrets\.([A-Z0-9_]+)",
                text
            )
        )
    )



def scan_references(files):

    references = {}

    all_text = {}

    for f in files:

        if f.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        all_text[str(f)] = read_text(f)



    for target in files:

        name = str(
            target.relative_to(ROOT)
        )

        used_by = []

        for source,text in all_text.items():

            if source == str(target):
                continue

            if name in text:

                used_by.append(
                    str(
                        Path(source).relative_to(ROOT)
                    )
                )


        references[name] = used_by


    return references



def find_duplicates(files):

    results = []

    xml_files = {}

    for f in files:

        if f.suffix == ".xml":

            xml_files[str(f)] = f


    for xml in xml_files:

        gz = Path(
            xml + ".gz"
        )

        if gz.exists():

            results.append({

                "xml": xml,
                "compressed": str(
                    gz.relative_to(ROOT)
                )

            })


    return results



def classify_files(files,references):

    output = []

    for f in files:

        rel = str(
            f.relative_to(ROOT)
        )

        refs = references.get(
            rel,
            []
        )

        age = get_age(f)

        if refs:

            status = "USED"

        elif (
            "guides" in rel
            or "output" in rel
        ):

            status = "POSSIBLY_GENERATED"

        else:

            status = "ORPHAN_CANDIDATE"


        output.append({

            "file": rel,
            "status": status,
            "days_old": age,
            "referenced_by": refs

        })


    return output



def write_report(data):

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2
        )


    with open(
        OUTPUT_TXT,
        "w",
        encoding="utf-8"
    ) as f:


        f.write(
            "REPOSITORY AUDIT REPORT\n"
        )

        f.write(
            "=======================\n\n"
        )


        f.write(
            "WORKFLOWS\n"
        )

        for w in data["workflows"]:

            f.write(
                f"\n{w['name']}\n"
            )

            f.write(
                f"File: {w['file']}\n"
            )

            if w["references"]:

                f.write(
                    "References:\n"
                )

                for r in w["references"]:
                    f.write(
                        f"  - {r}\n"
                    )


        f.write(
            "\n\nDUPLICATE GUIDES\n"
        )

        for d in data["duplicates"]:

            f.write(
                f"\n{d['xml']}\n"
            )

            f.write(
                f"  + {d['compressed']}\n"
            )


        f.write(
            "\n\nCLEANUP CANDIDATES\n"
        )


        for item in data["files"]:

            if item["status"] == "ORPHAN_CANDIDATE":

                f.write(
                    f"\n{item['file']}"
                )

                f.write(
                    f" ({item['days_old']} days old)"
                )



def main():

    print(
        "Scanning repository..."
    )

    files = scan_files()

    print(
        f"Found {len(files)} files"
    )


    workflows = find_workflows(files)

    references = scan_references(files)

    duplicates = find_duplicates(files)

    classifications = classify_files(
        files,
        references
    )


    data = {

        "generated":
            datetime.now().isoformat(),

        "workflows":
            workflows,

        "duplicates":
            duplicates,

        "files":
            classifications

    }


    write_report(data)


    print(
        "\nAudit complete"
    )

    print(
        OUTPUT_TXT
    )



if __name__ == "__main__":

    main()
