from __future__ import annotations

import re
from pathlib import Path


SPRING_REPOSITORY_BASES = {
    "JpaRepository",
    "CrudRepository",
    "PagingAndSortingRepository",
    "Repository",
}


JAVA_ANNOTATION_PATTERNS = {
    "controller": r"@(RestController|Controller)\b",
    "service": r"@Service\b",
    "entity": r"@Entity\b",
    "configuration": r"@Configuration\b",
    "component": r"@Component\b",
}


def _read_file(
    file_path: Path,
) -> str:
    return file_path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def _strip_comments(
    content: str,
) -> str:
    """
    Remove Java block comments, JavaDoc comments,
    and single-line comments.

    This prevents words inside comments such as
    'for', 'mainly', '@author', etc. from being
    interpreted as Java declarations.
    """

    content = re.sub(
        r"/\*.*?\*/",
        "",
        content,
        flags=re.DOTALL,
    )

    content = re.sub(
        r"//.*?$",
        "",
        content,
        flags=re.MULTILINE,
    )

    return content


def _extract_package(
    content: str,
) -> str | None:
    match = re.search(
        r"^\s*package\s+([\w.]+)\s*;",
        content,
        re.MULTILINE,
    )

    return (
        match.group(1)
        if match
        else None
    )


def _extract_imports(
    content: str,
) -> list[str]:
    return re.findall(
        r"^\s*import\s+([\w.*]+)\s*;",
        content,
        re.MULTILINE,
    )


def _extract_type_declaration(
    content: str,
) -> tuple[str | None, str | None]:
    """
    Return:
        declaration type
        declaration name

    Example:
        public class Owner
        -> ("class", "Owner")

        public interface OwnerRepository
        -> ("interface", "OwnerRepository")
    """

    pattern = re.compile(
        r"""
        (?:
            public\s+
            | protected\s+
            | private\s+
            | abstract\s+
            | final\s+
            | static\s+
            | sealed\s+
            | non-sealed\s+
        )*
        \b
        (class|interface|enum|record)
        \s+
        ([A-Za-z_][A-Za-z0-9_]*)
        """,
        re.VERBOSE,
    )

    match = pattern.search(
        content
    )

    if not match:
        return None, None

    return (
        match.group(1),
        match.group(2),
    )


def _is_spring_repository(
    content: str,
    imports: list[str],
    declaration_type: str | None,
) -> bool:
    if re.search(
        r"@Repository\b",
        content,
    ):
        return True

    if declaration_type != "interface":
        return False

    repository_import_detected = any(
        any(
            base in imported
            for base in SPRING_REPOSITORY_BASES
        )
        for imported in imports
    )

    if not repository_import_detected:
        return False

    extends_match = re.search(
        r"\binterface\s+\w+\s+extends\s+([^{]+)",
        content,
    )

    if not extends_match:
        return False

    inherited_types = (
        extends_match
        .group(1)
        .replace("\n", " ")
    )

    return any(
        base in inherited_types
        for base in SPRING_REPOSITORY_BASES
    )


def _extract_class_type(
    content: str,
    imports: list[str],
    declaration_type: str | None,
) -> str:
    if _is_spring_repository(
        content,
        imports,
        declaration_type,
    ):
        return "repository"

    for (
        class_type,
        pattern,
    ) in JAVA_ANNOTATION_PATTERNS.items():

        if re.search(
            pattern,
            content,
        ):
            return class_type

    if re.search(
        r"@MappedSuperclass\b",
        content,
    ):
        return "mapped_superclass"

    return (
        declaration_type
        or "class"
    )


def _extract_methods(
    content: str,
) -> list[str]:
    method_pattern = re.compile(
        r"""
        (?:
            public
            | protected
            | private
        )
        \s+
        (?:
            static\s+
        )?
        (?:
            final\s+
        )?
        [A-Za-z0-9_<>\[\],.?]+\s+
        ([A-Za-z_][A-Za-z0-9_]*)
        \s*
        \(
        [^)]*
        \)
        """,
        re.VERBOSE,
    )

    methods = method_pattern.findall(
        content
    )

    return sorted(
        set(methods)
    )


def _extract_annotations(
    content: str,
) -> list[str]:
    annotations = re.findall(
        r"@([A-Za-z_][A-Za-z0-9_]*)",
        content,
    )

    return sorted(
        set(annotations)
    )


def _is_test_file(
    file_path: Path,
) -> bool:
    normalized = (
        str(file_path)
        .replace("\\", "/")
        .lower()
    )

    return (
        "/src/test/" in normalized
        or file_path.name.endswith(
            "Test.java"
        )
        or file_path.name.endswith(
            "Tests.java"
        )
    )


def scan_java_structure(
    repo_path: Path,
) -> dict:
    classes = []

    controllers = []
    services = []
    repositories = []
    entities = []
    configurations = []
    components = []
    mapped_superclasses = []
    tests = []

    packages = set()

    for file_path in repo_path.rglob(
        "*.java"
    ):
        if ".git" in file_path.parts:
            continue

        if "target" in file_path.parts:
            continue

        raw_content = _read_file(
            file_path
        )

        content = _strip_comments(
            raw_content
        )

        package_name = _extract_package(
            content
        )

        if package_name:
            packages.add(
                package_name
            )

        imports = _extract_imports(
            content
        )

        (
            declaration_type,
            class_name,
        ) = _extract_type_declaration(
            content
        )

        if not class_name:
            continue

        class_type = _extract_class_type(
            content,
            imports,
            declaration_type,
        )

        relative_path = str(
            file_path.relative_to(
                repo_path
            )
        )

        class_info = {
            "name": class_name,
            "package": package_name,
            "file": relative_path,
            "declaration_type": (
                declaration_type
            ),
            "type": class_type,
            "imports": imports,
            "methods": _extract_methods(
                content
            ),
            "annotations": (
                _extract_annotations(
                    content
                )
            ),
            "is_test": _is_test_file(
                file_path
            ),
        }

        classes.append(
            class_info
        )

        if class_type == "controller":
            controllers.append(
                class_name
            )

        elif class_type == "service":
            services.append(
                class_name
            )

        elif class_type == "repository":
            repositories.append(
                class_name
            )

        elif class_type == "entity":
            entities.append(
                class_name
            )

        elif class_type == "configuration":
            configurations.append(
                class_name
            )

        elif class_type == "component":
            components.append(
                class_name
            )

        elif class_type == "mapped_superclass":
            mapped_superclasses.append(
                class_name
            )

        if _is_test_file(
            file_path
        ):
            tests.append(
                class_name
            )

    return {
        "packages": sorted(
            packages
        ),
        "classes": classes,
        "controllers": sorted(
            controllers
        ),
        "services": sorted(
            services
        ),
        "repositories": sorted(
            repositories
        ),
        "entities": sorted(
            entities
        ),
        "configurations": sorted(
            configurations
        ),
        "components": sorted(
            components
        ),
        "mapped_superclasses": sorted(
            mapped_superclasses
        ),
        "test_classes": sorted(
            tests
        ),
        "class_count": len(
            classes
        ),
    }