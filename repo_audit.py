from pathlib import Path
from datetime import datetime, timezone
import json
import re


ROOT = Path(__file__).resolve().parent

WORKFLOW_DIR = ROOT / ".github" / "workflows"

AUDIT_DIRECTORIES = [
    ROOT / "fast",
    ROOT / "guides",
    ROOT / "xtream-epg",
]

REPORT_FILE = ROOT / "repo_audit_report.txt"
JSON_FILE = ROOT / "repo_audit.json"


TEXT_EXTENSIONS = {
    ".yml",
    ".yaml",
    ".py",
    ".js",
    ".ts",
    ".json",
    ".txt",
    ".sh",
    ".xml",
    ".md",
    ".toml",
    ".ini",
    ".cfg",
}


def relative_path(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return ""


def all_repository_files():
    files = []

    for path in ROOT.rglob("*"):

        if not path.is_file():
            continue

        relative = relative_path(path)

        if relative.startswith(".git/"):
            continue

        if relative.startswith("logos/"):
            continue

        files.append(path)

    return files


def audit_scope_files():
    files = []

    for directory in AUDIT_DIRECTORIES:

        if not directory.exists():
            continue

        for path in directory.rglob("*"):

            if path.is_file():
                files.append(path)

    return sorted(files)


def workflow_files():
    if not WORKFLOW_DIR.exists():
        return []

    return sorted(
        path
        for path in WORKFLOW_DIR.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yml", ".yaml"}
    )


def normalize_reference(value):
    value = value.strip()

    value = value.strip(
        "\"'`"
    )

    value = value.replace(
        "${{ github.workspace }}/",
        ""
    )

    value = value.replace(
        "${GITHUB_WORKSPACE}/",
        ""
    )

    value = value.replace(
        "$GITHUB_WORKSPACE/",
        ""
    )

    value = value.lstrip("./")

    return value


def find_explicit_file_references(text, repository_files):
    references = set()

    known_paths = {
        relative_path(path): path
        for path in repository_files
    }

    for relative in known_paths:

        escaped = re.escape(relative)

        if re.search(
            rf"(?<![A-Za-z0-9_./-]){escaped}(?![A-Za-z0-9_./-])",
            text
        ):
            references.add(relative)

    return references


def find_filename_references(text, repository_files):
    references = set()

    for path in repository_files:

        filename = path.name

        if len(filename) < 4:
            continue

        if filename not in text:
            continue

        references.add(
            relative_path(path)
        )

    return references


def find_path_like_references(text, repository_files):
    references = set()

    known_paths = {
        relative_path(path): path
        for path in repository_files
    }

    candidates = re.findall(
        r"""
        (?:
            [A-Za-z0-9_.-]+/
        )+
        [A-Za-z0-9_.-]+
        (?:\.[A-Za-z0-9_.-]+)?
        """,
        text,
        re.VERBOSE
    )

    for candidate in candidates:

        candidate = normalize_reference(
            candidate
        )

        if candidate in known_paths:
            references.add(candidate)

    return references


def find_workflow_dependencies(workflow_path, repository_files):
    text = read_text(workflow_path)

    references = set()

    references.update(
        find_explicit_file_references(
            text,
            repository_files
        )
    )

    references.update(
        find_filename_references(
            text,
            repository_files
        )
    )

    references.update(
        find_path_like_references(
            text,
            repository_files
        )
    )

    return sorted(references)


def find_script_dependencies(
    script_path,
    repository_files,
    already_scanned=None
):
    if already_scanned is None:
        already_scanned = set()

    relative_script = relative_path(
        script_path
    )

    if relative_script in already_scanned:
        return set()

    already_scanned.add(
        relative_script
    )

    text = read_text(
        script_path
    )

    dependencies = set()

    dependencies.update(
        find_explicit_file_references(
            text,
            repository_files
        )
    )

    dependencies.update(
        find_filename_references(
            text,
            repository_files
        )
    )

    dependencies.update(
        find_path_like_references(
            text,
            repository_files
        )
    )

    script_extensions = {
        ".py",
        ".js",
        ".ts",
        ".sh"
    }

    for dependency in list(dependencies):

        dependency_path = ROOT / dependency

        if (
            dependency_path.exists()
            and dependency_path.is_file()
            and dependency_path.suffix.lower()
            in script_extensions
        ):
            dependencies.update(
                find_script_dependencies(
                    dependency_path,
                    repository_files,
                    already_scanned
                )
            )

    return dependencies


def build_audit():

    repository_files = all_repository_files()

    workflows = workflow_files()

    workflow_results = {}

    all_referenced = set()

    for workflow in workflows:

        workflow_relative = relative_path(
            workflow
        )

        direct_dependencies = find_workflow_dependencies(
            workflow,
            repository_files
        )

        all_dependencies = set(
            direct_dependencies
        )

        for dependency in list(
            direct_dependencies
        ):

            dependency_path = ROOT / dependency

            if (
                dependency_path.exists()
                and dependency_path.is_file()
                and dependency_path.suffix.lower()
                in {".py", ".js", ".ts", ".sh"}
            ):
                all_dependencies.update(
                    find_script_dependencies(
                        dependency_path,
                        repository_files
                    )
                )

        workflow_results[
            workflow_relative
        ] = sorted(
            all_dependencies
        )

        all_referenced.update(
            all_dependencies
        )

    scoped_files = audit_scope_files()

    scoped_relative = {
        relative_path(path)
        for path in scoped_files
    }

    referenced_scoped = sorted(
        scoped_relative.intersection(
            all_referenced
        )
    )

    unreferenced_scoped = sorted(
        scoped_relative.difference(
            all_referenced
        )
    )

    return {
        "generated": datetime.now(
            timezone.utc
        ).isoformat(),

        "audit_scope": [
            ".github/workflows/",
            "fast/",
            "guides/",
            "xtream-epg/"
        ],

        "workflows_analyzed": len(
            workflows
        ),

        "files_checked": len(
            scoped_files
        ),

        "files_referenced_by_workflows": len(
            referenced_scoped
        ),

        "files_not_referenced_by_workflows": len(
            unreferenced_scoped
        ),

        "referenced_files": referenced_scoped,

        "unreferenced_files": unreferenced_scoped,

        "workflow_dependencies": workflow_results
    }


def build_report(data):

    lines = []

    lines.append(
        "REPOSITORY WORKFLOW DEPENDENCY AUDIT"
    )

    lines.append(
        "===================================="
    )

    lines.append("")

    lines.append(
        f"Generated: {data['generated']}"
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
        f"Workflows analyzed: {data['workflows_analyzed']}"
    )

    lines.append(
        f"Files checked: {data['files_checked']}"
    )

    lines.append(
        f"Files referenced by workflows: "
        f"{data['files_referenced_by_workflows']}"
    )

    lines.append(
        f"Files not referenced by workflows: "
        f"{data['files_not_referenced_by_workflows']}"
    )

    lines.append("")

    lines.append(
        "FILES REFERENCED BY WORKFLOWS"
    )

    lines.append(
        "============================="
    )

    lines.append("")

    for path in data[
        "referenced_files"
    ]:
        lines.append(
            path
        )

    lines.append("")

    lines.append(
        "FILES NOT REFERENCED BY ANY WORKFLOW"
    )

    lines.append(
        "===================================="
    )

    lines.append("")

    if data[
        "unreferenced_files"
    ]:

        for path in data[
            "unreferenced_files"
        ]:
            lines.append(
                f"{path}"
            )

    else:

        lines.append(
            "None"
        )

    lines.append("")

    lines.append(
        "WORKFLOW DEPENDENCY MAP"
    )

    lines.append(
        "======================="
    )

    lines.append("")

    for workflow, dependencies in data[
        "workflow_dependencies"
    ].items():

        lines.append(
            workflow
        )

        if dependencies:

            for dependency in dependencies:

                lines.append(
                    f"  - {dependency}"
                )

        else:

            lines.append(
                "  No repository files detected"
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
        "The logos directory was ignored."
    )

    lines.append(
        "Files are only flagged for review."
    )

    lines.append(
        "Script dependencies are recursively scanned."
    )

    return "\n".join(
        lines
    )


def main():

    data = build_audit()

    REPORT_FILE.write_text(
        build_report(data),
        encoding="utf-8"
    )

    JSON_FILE.write_text(
        json.dumps(
            data,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"Audit complete: {REPORT_FILE}"
    )

    print(
        f"JSON written: {JSON_FILE}"
    )


if __name__ == "__main__":
    main()
