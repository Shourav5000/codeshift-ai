from __future__ import annotations

import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]

    return tag


def _text(
    element: ET.Element | None,
) -> str | None:
    if element is None:
        return None

    if element.text is None:
        return None

    value = element.text.strip()

    return value or None


def _resolve_property(
    value: str | None,
    properties: dict[str, str],
) -> str | None:
    if value is None:
        return None

    if (
        value.startswith("${")
        and value.endswith("}")
    ):
        property_name = value[2:-1]

        return properties.get(
            property_name,
            value,
        )

    return value


def _parse_maven_declared_dependencies(
    repo_path: Path,
) -> list[dict]:
    pom_file = (
        repo_path
        / "pom.xml"
    )

    if not pom_file.exists():
        return []

    try:
        tree = ET.parse(
            pom_file
        )

    except ET.ParseError:
        return []

    root = tree.getroot()

    properties: dict[
        str,
        str,
    ] = {}

    for child in root:
        if (
            _strip_namespace(
                child.tag
            )
            != "properties"
        ):
            continue

        for property_node in child:
            property_name = (
                _strip_namespace(
                    property_node.tag
                )
            )

            property_value = _text(
                property_node
            )

            if property_value:
                properties[
                    property_name
                ] = property_value

    dependencies: list[dict] = []

    for element in root.iter():
        if (
            _strip_namespace(
                element.tag
            )
            != "dependency"
        ):
            continue

        values = {
            _strip_namespace(
                child.tag
            ): _text(child)
            for child in element
        }

        group_id = values.get(
            "groupId"
        )

        artifact_id = values.get(
            "artifactId"
        )

        if (
            not group_id
            or not artifact_id
        ):
            continue

        version = _resolve_property(
            values.get(
                "version"
            ),
            properties,
        )

        scope = (
            values.get(
                "scope"
            )
            or "compile"
        )

        optional = (
            values.get(
                "optional"
            )
            == "true"
        )

        dependencies.append(
            {
                "ecosystem": "Maven",
                "group": group_id,
                "artifact": artifact_id,
                "version": version,
                "scope": scope,
                "optional": optional,
                "source": "pom.xml",
                "transitive": False,
            }
        )

    return dependencies


def _get_maven_command(
    repo_path: Path,
) -> list[str]:

    windows_wrapper = (
        repo_path
        / "mvnw.cmd"
    )

    unix_wrapper = (
        repo_path
        / "mvnw"
    )

    if (
        os.name == "nt"
        and windows_wrapper.exists()
    ):
        return [
            "cmd",
            "/c",
            str(windows_wrapper),
        ]

    if unix_wrapper.exists():
        return [
            str(unix_wrapper)
        ]

    if windows_wrapper.exists():
        return [
            "cmd",
            "/c",
            str(windows_wrapper),
        ]

    return [
        "mvn"
    ]


def _clean_maven_tree_line(
    raw_line: str,
) -> str:

    line = raw_line.strip()

    while line.startswith(
        (
            "+- ",
            "\\- ",
            "|  ",
            "   ",
        )
    ):
        if line.startswith(
            "+- "
        ):
            line = line[3:]

        elif line.startswith(
            "\\- "
        ):
            line = line[3:]

        elif line.startswith(
            "|  "
        ):
            line = line[3:]

        elif line.startswith(
            "   "
        ):
            line = line[3:]

        line = line.strip()

    return line


def _parse_maven_tree_dependency(
    line: str,
) -> dict | None:

    parts = [
        part.strip()
        for part in line.split(":")
    ]

    if len(parts) < 5:
        return None

    group_id = parts[0]
    artifact_id = parts[1]
    packaging = parts[2]

    # Maven can include a classifier:
    #
    # group:artifact:type:version:scope
    #
    # or:
    #
    # group:artifact:type:classifier:version:scope

    if len(parts) == 5:
        version = parts[3]
        scope = parts[4]

    else:
        version = parts[-2]
        scope = parts[-1]

    if not (
        group_id
        and artifact_id
        and version
    ):
        return None

    return {
        "ecosystem": "Maven",
        "group": group_id,
        "artifact": artifact_id,
        "version": version,
        "scope": scope,
        "packaging": packaging,
        "optional": False,
        "source": (
            "maven_dependency_tree"
        ),
    }


def _run_maven_dependency_tree(
    repo_path: Path,
) -> list[dict]:

    pom_file = (
        repo_path
        / "pom.xml"
    )

    if not pom_file.exists():
        return []

    output_file = (
        repo_path
        / ".codeshift-dependency-tree.txt"
    )

    maven_command = (
        _get_maven_command(
            repo_path
        )
    )

    command = (
        maven_command
        + [
            "-q",
            "dependency:tree",
            "-DoutputType=text",
            (
                "-DoutputFile="
                f"{output_file.name}"
            ),
        ]
    )

    try:
        subprocess.run(
            command,
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )

    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ):
        return []

    if not output_file.exists():
        return []

    try:
        content = (
            output_file.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

    finally:
        try:
            output_file.unlink()

        except OSError:
            pass

    dependencies: list[dict] = []

    for raw_line in (
        content.splitlines()
    ):
        line = (
            _clean_maven_tree_line(
                raw_line
            )
        )

        if not line:
            continue

        dependency = (
            _parse_maven_tree_dependency(
                line
            )
        )

        if dependency is None:
            continue

        dependencies.append(
            dependency
        )

    return dependencies


def _merge_maven_dependencies(
    declared_dependencies: list[dict],
    resolved_dependencies: list[dict],
) -> list[dict]:

    resolved_lookup: dict[
        tuple[str, str],
        dict,
    ] = {}

    for dependency in (
        resolved_dependencies
    ):
        group = dependency.get(
            "group"
        )

        artifact = dependency.get(
            "artifact"
        )

        if not group or not artifact:
            continue

        key = (
            str(group),
            str(artifact),
        )

        resolved_lookup[key] = (
            dependency
        )

    merged: list[dict] = []

    seen: set[
        tuple[str, str]
    ] = set()

    for dependency in (
        declared_dependencies
    ):
        group = dependency.get(
            "group"
        )

        artifact = dependency.get(
            "artifact"
        )

        if not group or not artifact:
            continue

        key = (
            str(group),
            str(artifact),
        )

        resolved = (
            resolved_lookup.get(
                key
            )
        )

        if resolved:
            merged_dependency = {
                **dependency,
                "version": (
                    resolved.get(
                        "version"
                    )
                ),
                "scope": (
                    resolved.get(
                        "scope",
                        dependency.get(
                            "scope",
                            "compile",
                        ),
                    )
                ),
                "resolved": True,
                "transitive": False,
                "resolution_source": (
                    "maven_dependency_tree"
                ),
            }

        else:
            declared_version = (
                dependency.get(
                    "version"
                )
            )

            resolved_from_pom = bool(
                declared_version
                and not str(
                    declared_version
                ).startswith("${")
            )

            merged_dependency = {
                **dependency,
                "resolved": (
                    resolved_from_pom
                ),
                "transitive": False,
                "resolution_source": (
                    "pom.xml"
                ),
            }

        merged.append(
            merged_dependency
        )

        seen.add(key)

    for dependency in (
        resolved_dependencies
    ):
        group = dependency.get(
            "group"
        )

        artifact = dependency.get(
            "artifact"
        )

        if not group or not artifact:
            continue

        key = (
            str(group),
            str(artifact),
        )

        if key in seen:
            continue

        merged.append(
            {
                **dependency,
                "resolved": True,
                "transitive": True,
                "resolution_source": (
                    "maven_dependency_tree"
                ),
            }
        )

        seen.add(key)

    return merged


def _parse_npm_dependencies(
    repo_path: Path,
) -> list[dict]:

    package_file = (
        repo_path
        / "package.json"
    )

    if not package_file.exists():
        return []

    try:
        package_data = json.loads(
            package_file.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )

    except json.JSONDecodeError:
        return []

    dependencies: list[dict] = []

    dependency_groups = {
        "dependencies": "runtime",
        "devDependencies": (
            "development"
        ),
        "peerDependencies": "peer",
        "optionalDependencies": (
            "optional"
        ),
    }

    for (
        group_name,
        dependency_scope,
    ) in dependency_groups.items():

        dependency_group = (
            package_data.get(
                group_name,
                {},
            )
        )

        if not isinstance(
            dependency_group,
            dict,
        ):
            continue

        for (
            package_name,
            version,
        ) in dependency_group.items():

            dependencies.append(
                {
                    "ecosystem": "npm",
                    "package": (
                        package_name
                    ),
                    "version": version,
                    "scope": (
                        dependency_scope
                    ),
                    "resolved": False,
                    "transitive": False,
                    "source": (
                        "package.json"
                    ),
                    "resolution_source": (
                        "package.json"
                    ),
                }
            )

    return dependencies


IGNORED_PROJECT_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".next",
}


def _project_path_is_ignored(
    path: Path,
    repo_path: Path,
) -> bool:
    try:
        relative = path.relative_to(
            repo_path
        )
    except ValueError:
        relative = path

    return any(
        part in IGNORED_PROJECT_DIRECTORIES
        for part in relative.parts
    )


def _find_manifest_roots(
    repo_path: Path,
    filename: str,
) -> list[Path]:
    roots = {
        path.parent.resolve()
        for path in repo_path.rglob(
            filename
        )
        if path.is_file()
        and not _project_path_is_ignored(
            path,
            repo_path,
        )
    }

    return sorted(
        roots,
        key=lambda path: (
            len(
                path.relative_to(
                    repo_path
                ).parts
            ),
            path.as_posix(),
        ),
    )


def _relative_project_path(
    project_root: Path,
    repo_path: Path,
) -> str:
    relative = project_root.relative_to(
        repo_path
    )

    value = relative.as_posix()

    return value or "."


def _dependency_identity(
    dependency: dict,
) -> tuple:
    ecosystem = dependency.get(
        "ecosystem"
    )

    if ecosystem == "Maven":
        return (
            "Maven",
            dependency.get(
                "group"
            ),
            dependency.get(
                "artifact"
            ),
            dependency.get(
                "version"
            ),
            dependency.get(
                "scope"
            ),
        )

    if ecosystem == "npm":
        return (
            "npm",
            dependency.get(
                "package"
            ),
            dependency.get(
                "version"
            ),
            dependency.get(
                "scope"
            ),
        )

    return (
        str(ecosystem),
        str(dependency),
    )


def _aggregate_dependencies(
    dependencies: list[dict],
) -> list[dict]:
    aggregated: dict[
        tuple,
        dict,
    ] = {}

    for dependency in dependencies:
        key = _dependency_identity(
            dependency
        )

        project_path = (
            dependency.get(
                "project_path"
            )
            or "."
        )

        if key not in aggregated:
            item = {
                **dependency,
                "project_paths": [
                    project_path
                ],
            }

            aggregated[
                key
            ] = item

            continue

        existing = aggregated[
            key
        ]

        project_paths = existing.get(
            "project_paths",
            [],
        )

        if (
            project_path
            not in project_paths
        ):
            project_paths.append(
                project_path
            )

        existing[
            "project_paths"
        ] = sorted(
            project_paths
        )

        existing[
            "resolved"
        ] = bool(
            existing.get(
                "resolved",
                False,
            )
            or dependency.get(
                "resolved",
                False,
            )
        )

        existing[
            "transitive"
        ] = bool(
            existing.get(
                "transitive",
                False,
            )
            and dependency.get(
                "transitive",
                False,
            )
        )

        if dependency.get(
            "resolution_source"
        ) == "maven_dependency_tree":
            existing[
                "resolution_source"
            ] = (
                "maven_dependency_tree"
            )

    return list(
        aggregated.values()
    )


def scan_dependencies(
    repo_path: Path,
) -> dict:
    repo_path = Path(
        repo_path
    ).resolve()

    all_dependencies: list[
        dict
    ] = []

    dependency_projects: list[
        dict
    ] = []

    maven_resolution_used = (
        False
    )

    maven_projects = (
        _find_manifest_roots(
            repo_path,
            "pom.xml",
        )
    )

    for project_root in (
        maven_projects
    ):
        declared = (
            _parse_maven_declared_dependencies(
                project_root
            )
        )

        resolved = (
            _run_maven_dependency_tree(
                project_root
            )
        )

        if resolved:
            maven_resolution_used = (
                True
            )

        merged = (
            _merge_maven_dependencies(
                declared,
                resolved,
            )
        )

        project_path = (
            _relative_project_path(
                project_root,
                repo_path,
            )
        )

        for dependency in merged:
            all_dependencies.append(
                {
                    **dependency,
                    "project_path": (
                        project_path
                    ),
                }
            )

        dependency_projects.append(
            {
                "project_path": (
                    project_path
                ),
                "ecosystem": (
                    "Maven"
                ),
                "dependency_count": (
                    len(merged)
                ),
            }
        )

    npm_projects = (
        _find_manifest_roots(
            repo_path,
            "package.json",
        )
    )

    for project_root in (
        npm_projects
    ):
        dependencies = (
            _parse_npm_dependencies(
                project_root
            )
        )

        project_path = (
            _relative_project_path(
                project_root,
                repo_path,
            )
        )

        for dependency in dependencies:
            all_dependencies.append(
                {
                    **dependency,
                    "project_path": (
                        project_path
                    ),
                }
            )

        dependency_projects.append(
            {
                "project_path": (
                    project_path
                ),
                "ecosystem": "npm",
                "dependency_count": (
                    len(dependencies)
                ),
            }
        )

    all_dependencies = (
        _aggregate_dependencies(
            all_dependencies
        )
    )

    ecosystems: list[str] = []

    if maven_projects:
        ecosystems.append(
            "Maven"
        )

    if npm_projects:
        ecosystems.append(
            "npm"
        )

    resolved_count = sum(
        1
        for dependency
        in all_dependencies
        if dependency.get(
            "resolved",
            False,
        )
    )

    unresolved_count = (
        len(all_dependencies)
        - resolved_count
    )

    direct_count = sum(
        1
        for dependency
        in all_dependencies
        if not dependency.get(
            "transitive",
            False,
        )
    )

    transitive_count = sum(
        1
        for dependency
        in all_dependencies
        if dependency.get(
            "transitive",
            False,
        )
    )

    return {
        "ecosystems": (
            ecosystems
        ),
        "dependencies": (
            all_dependencies
        ),
        "dependency_count": (
            len(
                all_dependencies
            )
        ),
        "resolved_dependency_count": (
            resolved_count
        ),
        "unresolved_dependency_count": (
            unresolved_count
        ),
        "direct_dependency_count": (
            direct_count
        ),
        "transitive_dependency_count": (
            transitive_count
        ),
        "maven_resolution_used": (
            maven_resolution_used
        ),
        "projects": (
            dependency_projects
        ),
    }
