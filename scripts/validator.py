"""
Validation module for awesome-european-opensource entities.

Provides a flexible validation framework that can be extended for different entity types
(projects, events, companies, etc.) using JSON Schema validation.
"""

import json
import os
import sys
from typing import Any

import fastjsonschema


PROJECT_ROOTDIR = os.path.dirname(os.path.abspath(__file__).replace("scripts/", ""))


def get_jsonschema(name: str) -> dict[str, Any]:
    """Load JSON schema from schemas directory.

    Args:
        name: Schema name (without .json extension)

    Returns:
        Parsed JSON schema as dictionary

    Raises:
        FileNotFoundError: If schema file doesn't exist
    """
    schema_path = f"{PROJECT_ROOTDIR}/schemas/{name}.json"
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


class Validator:
    """Base validator class for entities using JSON Schema validation.

    Subclasses should define:
        - schema_name: Name of the JSON schema file (without .json)
        - source_filepath: Default directory path for validation
    """

    schema_name: str | None = None
    source_filepath: str | None = None

    def __init__(self) -> None:
        """Initialize validator with compiled JSON schema."""
        if self.schema_name is None:
            raise NotImplementedError("schema_name must be defined in subclass")

        self.schema_configuration = fastjsonschema.compile(
            definition=get_jsonschema(self.schema_name)
        )
        self.source_data: dict[str, dict[str, Any]] = {}
        self.metadata = {
            "success": 0,
            "failed": 0,
            "warning": 0,
            "total": 0,
            "errors": [],
            "warnings": [],
        }

    def save_state(self, name: str, message: str, key: str = "errors") -> None:
        """Persist a validation outcome.

        Args:
            name: Entity name for identification
            message: Error or warning message
            key: Either "errors" or "warnings"

        Raises:
            ValueError: If key is not "errors" or "warnings"
        """
        if key not in ("errors", "warnings"):
            raise ValueError(f"Unsupported key '{key}' in save_state")

        entry = {"name": name, "message": message}
        self.metadata[key].append(entry)

        if key == "errors":
            self.metadata["failed"] += 1
        elif key == "warnings":
            self.metadata["warning"] += 1

    def validate(
        self,
        filename: str | None = None,
        data: dict[str, Any] | None = None,
        check_file_exists: bool = True,
    ) -> tuple[dict[str, Any] | None, list[dict[str, str]] | None]:
        """Validate entity data against JSON schema.

        Args:
            filename: Path to JSON file to validate
            data: Dictionary data to validate directly
            check_file_exists: Whether to check if file already exists (for duplicate detection).
                              Set to False when validating existing files from directory.

        Returns:
            Tuple of (validated_data, errors) where errors is None on success

        Raises:
            ValueError: If neither filename nor data provided
        """
        if not filename and not data:
            raise ValueError("You must provide either filename or data")

        # Load data from file if filename provided
        if filename:
            if not os.path.isfile(filename):
                print(f"  [WARN] Not found {os.path.basename(filename)}")
                self.save_state(filename, f"File not found: {filename}", "warnings")
                return {}, None

            with open(filename, encoding="utf-8") as f:
                data = json.load(f)

        entity_name = data.get("name", "Unknown")

        try:
            print(f"[VALIDATE] {entity_name}")

            # Validate against schema
            self.schema_configuration(data)

            # Check for duplicate files only if requested (e.g., during import)
            if (
                check_file_exists
                and "metadata" in data
                and "filepath" in data["metadata"]
            ):
                relative_filepath = data["metadata"]["filepath"]
                absolute_filepath = os.path.join(PROJECT_ROOTDIR, relative_filepath)

                if os.path.isfile(absolute_filepath):
                    warning_msg = (
                        f"Entity '{entity_name}' already exists. "
                        f"File: {data['metadata']['filename']}"
                    )
                    print(f"  [WARN] {warning_msg}")
                    self.save_state(entity_name, warning_msg, "warnings")
                    return data, None

            self.metadata["success"] += 1
            return data, None

        except fastjsonschema.JsonSchemaException as e:
            print(f"  [ERROR] {entity_name} - {e.message}")
            self.save_state(entity_name, e.message)
            return None, self.metadata["errors"]

        except json.JSONDecodeError as e:
            print(f"  [ERROR] {entity_name} - {e.msg}")
            self.save_state(entity_name, e.msg)
            return None, self.metadata["errors"]

        except Exception as e:
            print(f"  [ERROR] {entity_name} - {str(e)}")
            self.save_state(entity_name, str(e))
            return None, self.metadata["errors"]

        finally:
            self.metadata["total"] += 1

    def execute(self, dirpath: str) -> dict[str, dict[str, Any]]:
        """Execute validation on all JSON files in directory.

        Args:
            dirpath: Directory containing JSON files to validate

        Returns:
            Dictionary mapping entity IDs to validated data

        Raises:
            NotADirectoryError: If dirpath is not a valid directory
        """
        print(f"[INFO] Validating {dirpath} directory")

        if not os.path.isdir(dirpath):
            raise NotADirectoryError(f"Directory not found: {dirpath}")

        # Collect valid JSON files
        json_files = []
        for entry in os.listdir(dirpath):
            filepath = os.path.join(dirpath, entry)

            if not os.path.isfile(filepath):
                print(f"  [WARN] Skipping non-file: {entry}")
                self.save_state(entry, "Not a file", "warnings")
                continue

            if not entry.endswith(".json"):
                print(f"  [WARN] Skipping non-JSON file: {entry}")
                self.save_state(
                    entry, "Invalid file extension (expected .json)", "warnings"
                )
                continue

            entity_id = entry.replace(".json", "")
            json_files.append((entity_id, filepath))

        # Validate files in sorted order (don't check if file exists - we're validating existing files)
        for entity_id, filepath in sorted(json_files, key=lambda x: x[0]):
            validated_data, _ = self.validate(
                filename=filepath, check_file_exists=False
            )
            if validated_data:
                self.source_data[entity_id] = validated_data

        return self.source_data

    def print(self) -> None:
        """Print validation summary and details."""
        entity_type = self.schema_name or "entities"

        print(f"\n[INFO] === Validation Summary for {entity_type} ===")
        print(f"[INFO] Total scanned: {self.metadata['total']}")
        print(f"[INFO] Successful: {self.metadata['success']}")
        print(f"[INFO] Failed: {self.metadata['failed']}")
        print(f"[INFO] Warnings: {self.metadata['warning']}")

        if self.metadata["errors"]:
            print("\n[ERROR] Validation Errors:")
            for error in self.metadata["errors"]:
                print(f"  ✗ {error['name']}: {error['message']}")
        else:
            print("\n[INFO] ✓ No validation errors found")

        if self.metadata["warnings"]:
            print("\n[WARN] Warnings:")
            for warning in self.metadata["warnings"]:
                print(f"  ⚠ {warning['name']}: {warning['message']}")

    def run(self) -> None:
        """Execute validation workflow and print results.

        Raises:
            NotImplementedError: If source_filepath not defined in subclass
        """
        if self.source_filepath is None:
            raise NotImplementedError("source_filepath must be defined in subclass")

        self.execute(self.source_filepath)
        self.print()

    def raise_on_error(self) -> None:
        """Raise exception if validation found errors.

        Raises:
            RuntimeError: If any validation errors occurred
        """
        sys.tracebacklimit = 0
        if self.metadata["failed"] > 0:
            raise RuntimeError(
                f"Validation failed with {self.metadata['failed']} error(s)"
            )

    @property
    def data(self) -> dict[str, dict[str, Any]]:
        """Get validated entity data."""
        return self.source_data

    def __str__(self) -> str:
        """String representation of validator state."""
        return (
            f"Validator({self.schema_name}): "
            f"{self.metadata['success']}/{self.metadata['total']} successful, "
            f"{self.metadata['failed']} errors, "
            f"{self.metadata['warning']} warnings"
        )


class ProjectValidator(Validator):
    """Validator for open-source project entities."""

    schema_name = "project"
    source_filepath = f"{PROJECT_ROOTDIR}/awesome/projects"


# Example: Additional validator types can be easily added
# class EventValidator(Validator):
#     """Validator for event entities."""
#     schema_name = "event"
#     source_filepath = f"{PROJECT_ROOTDIR}/awesome/events"
#
# class CompanyValidator(Validator):
#     """Validator for company entities."""
#     schema_name = "company"
#     source_filepath = f"{PROJECT_ROOTDIR}/awesome/companies"


def main() -> int:
    """Main entry point for validation script."""
    try:
        projects = ProjectValidator()
        projects.run()
        projects.raise_on_error()
        return 0
    except Exception as e:
        print(f"\n[FATAL] Validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
