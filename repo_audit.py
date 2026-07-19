from pathlib import Path
from collections import defaultdict
from datetime import datetime
import re
import yaml


ROOT = Path(__file__).resolve().parent

WORKFLOWS_DIR = (
    ROOT
    / ".github"
    / "workflows"
)

REPORT_FILE = (
    ROOT
    / "repo_audit_report.txt"
)


COMMAND_FILE_PATTERNS = [
    r"\bpython(?:3)?\s+([^\s;&|]+)",
    r"\bnode\s+([^\s;&|]+)",
    r"\bbash\s+([^\s;&|]+)",
    r"\bsh\s+([^\s;&|]+)",
    r"\bcat\s+([^\s;&|>]+)",
    r"\bgzip\s+([^\s;&|]+)",
    r"\bgunzip\s+([^\s;&|]+)",
    r"\b(?:cp|mv|rm)\s+(?:-[^\s]+\s+)*([^\s;&|]+)",
]


def normalize_path(value):

    value = value.strip()

    value = value.strip(
        "'\"`"
    )

    value = value.rstrip(
        ".,;:)"
    )

    value = value.replace(
        "${{ github.workspace }}/",
        ""
    )

    value = value.replace(
        "$GITHUB_WORKSPACE/",
        ""
    )

    if value.startswith("./"):

        value = value[2:]

    return value


def is_probable_path(value):

    if not value:

        return False

    if value.startswith("$"):

        return False

    if value.startswith(
        (
            "http://",
            "https://",
        )
    ):

        return False

    if value in {

        "true",
        "false",
        "null",
        "echo",
        "then",
        "fi",
        "done",

    }:

        return False

    return (

        "/" in value

        or value.endswith(
            (
                ".py",
                ".js",
                ".ts",
                ".sh",
                ".xml",
                ".gz",
                ".json",
                ".txt",
                ".yml",
                ".yaml",
            )
        )

    )


def extract_urls(text):

    return sorted(
        set(
            re.findall(
                r"https?://[^\s\"'<>]+",
                text,
            )
        )
    )


def extract_paths_from_command(command):

    found = set()

    for pattern in COMMAND_FILE_PATTERNS:

        matches = re.findall(
            pattern,
            command,
        )

        for match in matches:

            path = normalize_path(
                match
            )

            if is_probable_path(path):

                found.add(path)

    return found


def extract_workflow_commands(node):

    commands = []

    if isinstance(node, dict):

        for key, value in node.items():

            if key == "run":

                if isinstance(
                    value,
                    str,
                ):

                    commands.append(
                        value
                    )

            commands.extend(
                extract_workflow_commands(
                    value
                )
            )

    elif isinstance(node, list):

        for item in node:

            commands.extend(
                extract_workflow_commands(
                    item
                )
            )

    return commands


def extract_workflow_name(
    data,
    path,
):

    if isinstance(
        data,
        dict,
    ):

        name = data.get(
            "name"
        )

        if isinstance(
            name,
            str,
        ):

            return name

    return path.stem


def classify_path(path):

    if path.startswith(
        "/tmp/"
    ):

        return "TEMPORARY"

    if path.startswith(
        ".github/workflows/"
    ):

        return "WORKFLOW"

    if path.startswith(
        "guides/"
    ):

        return "GUIDE / OUTPUT"

    if path.startswith(
        "logos/"
    ):

        return "LOGO / ASSET"

    if path.startswith(
        "scripts/"
    ):

        return "SCRIPT"

    if path.endswith(
        (
            ".py",
            ".js",
            ".ts",
            ".sh",
        )
    ):

        return "SCRIPT"

    if path.endswith(
        (
            ".xml",
            ".gz",
        )
    ):

        return "DATA / GUIDE"

    return "OTHER"


def build_file_index():

    index = {}

    for path in ROOT.rglob("*"):

        if not path.is_file():

            continue

        if ".git" in path.parts:

            continue

        relative = path.relative_to(
            ROOT
        ).as_posix()

        index[relative] = {

            "path": relative,

            "size": path.stat().st_size,

            "modified": datetime.fromtimestamp(
                path.stat().st_mtime
            ).isoformat(
                timespec="seconds"
            ),

        }

    return index


def main():

    file_index = build_file_index()

    workflows = []

    referenced_by = defaultdict(
        set
    )

    workflow_paths = set()

    for workflow_path in sorted(
        WORKFLOWS_DIR.glob("*")
    ):

        if workflow_path.suffix not in {

            ".yml",
            ".yaml",

        }:

            continue

        relative_workflow = (
            workflow_path
            .relative_to(ROOT)
            .as_posix()
        )

        workflow_paths.add(
            relative_workflow
        )

        try:

            text = workflow_path.read_text(
                encoding="utf-8"
            )

            data = yaml.safe_load(
                text
            )

        except Exception as error:

            workflows.append(

                {

                    "name": workflow_path.stem,

                    "file": relative_workflow,

                    "error": str(error),

                    "commands": [],

                    "paths": set(),

                    "urls": set(),

                }

            )

            continue

        commands = (
            extract_workflow_commands(
                data
            )
        )

        paths = set()

        urls = set()

        for command in commands:

            paths.update(
                extract_paths_from_command(
                    command
                )
            )

            urls.update(
                extract_urls(
                    command
                )
            )

        paths.discard(
            relative_workflow
        )

        for path in paths:

            if path in file_index:

                referenced_by[path].add(
                    relative_workflow
                )

        workflows.append(

            {

                "name": extract_workflow_name(
                    data,
                    workflow_path,
                ),

                "file": relative_workflow,

                "error": None,

                "commands": commands,

                "paths": paths,

                "urls": urls,

            }

        )

    report = []

    report.append(
        "REPOSITORY WORKFLOW DEPENDENCY AUDIT"
    )

    report.append(
        "==================================="
    )

    report.append("")

    report.append(
        "Generated: "
        + datetime.now().isoformat()
    )

    report.append("")

    report.append(
        "SUMMARY"
    )

    report.append(
        "-------"
    )

    report.append(
        f"total_files: {len(file_index)}"
    )

    report.append(
        f"workflows: {len(workflows)}"
    )

    report.append(
        "files_directly_referenced_by_workflows: "
        f"{len(referenced_by)}"
    )

    report.append(
        "files_not_directly_referenced: "
        f"{len(file_index) - len(referenced_by)}"
    )

    report.append("")

    report.append(
        "WORKFLOW DEPENDENCY MAP"
    )

    report.append(
        "======================="
    )

    for workflow in workflows:

        report.append("")

        report.append(
            workflow["name"]
        )

        report.append(
            "-" * len(
                workflow["name"]
            )
        )

        report.append(
            "Workflow: "
            + workflow["file"]
        )

        if workflow["error"]:

            report.append(
                "ERROR: "
                + workflow["error"]
            )

            continue

        if workflow["urls"]:

            report.append("")

            report.append(
                "REMOTE SOURCES:"
            )

            for url in sorted(
                workflow["urls"]
            ):

                report.append(
                    "  - "
                    + url
                )

        if workflow["paths"]:

            report.append("")

            report.append(
                "FILES REFERENCED BY WORKFLOW:"
            )

            for path in sorted(
                workflow["paths"]
            ):

                category = classify_path(
                    path
                )

                exists = (
                    path in file_index
                )

                if exists:

                    status = (
                        "EXISTS IN REPOSITORY"
                    )

                elif path.startswith(
                    "/tmp/"
                ):

                    status = (
                        "TEMPORARY / CREATED DURING RUN"
                    )

                else:

                    status = (
                        "NOT FOUND IN REPOSITORY"
                    )

                report.append(
                    "  - "
                    + path
                )

                report.append(
                    "      Type: "
                    + category
                )

                report.append(
                    "      Status: "
                    + status
                )

        report.append("")

        report.append(
            "COMMANDS EXECUTED:"
        )

        for command in workflow[
            "commands"
        ]:

            for line in command.splitlines():

                line = line.strip()

                if line:

                    report.append(
                        "  $ "
                        + line
                    )

    report.append("")

    report.append(
        "FILE USAGE SUMMARY"
    )

    report.append(
        "=================="
    )

    for path in sorted(
        file_index
    ):

        users = sorted(
            referenced_by.get(
                path,
                set(),
            )
        )

        report.append("")

        report.append(
            path
        )

        if users:

            report.append(
                "  STATUS: USED BY WORKFLOW"
            )

            report.append(
                "  USED BY:"
            )

            for workflow in users:

                report.append(
                    "    - "
                    + workflow
                )

        else:

            report.append(
                "  STATUS: NOT DIRECTLY FOUND "
                "IN WORKFLOW COMMANDS"
            )

    report.append("")

    report.append(
        "POSSIBLE ORPHANS"
    )

    report.append(
        "================"
    )

    for path in sorted(
        file_index
    ):

        if path in workflow_paths:

            continue

        if path not in referenced_by:

            report.append("")

            report.append(
                path
            )

            report.append(
                "  REVIEW ONLY"
            )

            report.append(
                "  No direct workflow command reference found."
            )

            report.append(
                "  Nothing was deleted automatically."
            )

    REPORT_FILE.write_text(
        "\n".join(
            report
        ),
        encoding="utf-8",
    )

    print(
        "Audit complete:"
    )

    print(
        REPORT_FILE
    )


if __name__ == "__main__":

    main()
