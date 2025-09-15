"""
Import module for awesome-european-opensource entities.

Provides a flexible import framework that can handle different entity types
(projects, events, companies, etc.) from CSV files into structured JSON files.
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import unicodedata
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from validator import ProjectValidator, Validator


PROJECT_ROOTDIR = os.path.dirname(os.path.abspath(__file__).replace("scripts/", ""))


def normalize_name(name: str) -> str:
    """Normalize entity name for use in filenames.

    Removes accents, converts to lowercase, and replaces spaces with hyphens.

    Args:
        name: Original entity name

    Returns:
        Normalized name suitable for filenames
    """
    # Remove accents using Unicode normalization
    name_without_accents = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )
    # Convert to lowercase and replace spaces with hyphens
    return name_without_accents.replace(" ", "-").lower()


def generate_filename(name: str, unique_identifier: str) -> str:
    """Generate unique filename for entity.

    Args:
        name: Entity name
        unique_identifier: String to ensure uniqueness (e.g., URL)

    Returns:
        Filename in format: normalized-name-hash.json
    """
    normalized_name = normalize_name(name)
    unique_string = f"{normalized_name}:{unique_identifier}"
    hash_suffix = hashlib.sha256(unique_string.encode()).hexdigest()[:6]
    return f"{normalized_name}-{hash_suffix}.json"


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO 8601 formatted timestamp string
    """
    return datetime.now(UTC).isoformat()[:-13] + "Z"


class Importer(ABC):
    """Abstract base class for importing entities from CSV to JSON.

    Subclasses must implement:
        - transform_row: Convert CSV row to entity data structure
    """

    def __init__(self, csv_filepath: str, output_dir: str, validator: Validator):
        """Initialize importer.

        Args:
            csv_filepath: Path to source CSV file
            output_dir: Directory to save JSON files
            validator: Validator instance for entity type

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            NotADirectoryError: If output directory doesn't exist
            TypeError: If validator is not a Validator instance
        """
        if not os.path.isfile(csv_filepath):
            raise FileNotFoundError(f"CSV file not found: {csv_filepath}")

        if not os.path.isdir(output_dir):
            raise NotADirectoryError(f"Output directory not found: {output_dir}")

        if not isinstance(validator, Validator):
            raise TypeError(
                f"Validator must be an instance of Validator class, got {type(validator)}"
            )

        self.csv_filepath = csv_filepath
        self.output_dir = output_dir
        self.validator = validator

    def load_csv(self) -> list[dict[str, str]]:
        """Load data from CSV file.

        Returns:
            List of dictionaries representing CSV rows

        Raises:
            FileNotFoundError: If CSV file doesn't exist
        """
        print(f"[INFO] Loading data from {self.csv_filepath}")

        if not os.path.exists(self.csv_filepath):
            raise FileNotFoundError(f"CSV file not found: {self.csv_filepath}")

        with open(self.csv_filepath, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)

    @abstractmethod
    def transform_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Transform CSV row into entity data structure.

        Args:
            row: Dictionary representing a CSV row

        Returns:
            Transformed entity data ready for validation
        """
        pass

    def execute(self) -> None:
        """Execute import process: load CSV, transform, validate, and save."""
        data = self.load_csv()

        for row in data:
            try:
                entity_data = self.transform_row(row)
                entity_name = entity_data["name"]

                print(f"  [INFO] Processing: {entity_name}")

                # Validate entity data
                validated_data, errors = self.validator.validate(data=entity_data)

                if errors:
                    print(
                        f"  [DEBUG] Transformed data: \n{json.dumps(entity_data, indent=2)}"
                    )
                    sys.tracebacklimit = 0
                    raise RuntimeError(f"Validation failed for {entity_name}")

                # Save to JSON file (convert relative path to absolute for file operations)
                relative_filepath = validated_data["metadata"]["filepath"]
                absolute_filepath = os.path.join(PROJECT_ROOTDIR, relative_filepath)

                with open(absolute_filepath, mode="w", encoding="utf-8") as json_file:
                    json.dump(validated_data, json_file, indent=2, ensure_ascii=False)

                print(f"  [INFO] ✓ Created {entity_name}")

            except Exception as e:
                print(f"  [ERROR] Failed to process row: {e}")
                raise

    def run(self) -> None:
        """Run the import process and print summary."""
        self.execute()
        print(f"\n{self.validator}")


class ProjectImporter(Importer):
    """Importer for open-source project entities."""

    def __init__(self, csv_filepath: str, output_dir: str):
        """Initialize project importer with ProjectValidator."""
        super().__init__(csv_filepath, output_dir, ProjectValidator())

    def _build_owner_data(self, row: dict[str, str]) -> dict[str, Any]:
        """Build owner data structure based on owner type.

        Args:
            row: CSV row with owner information

        Returns:
            Owner data dictionary
        """
        owner_type = row["Who is the owner of this project?"]

        if owner_type == "Organization":
            owner = {
                "type": "organization",
                "name": row["Company Name"],
                "url_website": row["Company Website"],
                "is_a_startup": row["Your company is a Startup?"],
            }
            if row.get("Company Description"):
                owner["description"] = row["Company Description"]
            return owner

        elif owner_type == "Individual":
            return {
                "type": "individual",
                "name": row["Owner Full Name or Username"],
            }

        elif owner_type == "Community":
            owner = {
                "type": "community",
                "name": row["Community Name"],
                "url_website": row["Community Website"],
            }
            if row.get("Community Description"):
                owner["description"] = row["Community Description"]
            return owner

        else:
            raise ValueError(f"Unknown owner type: {owner_type}")

    def transform_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Transform CSV row into project data structure.

        Args:
            row: Dictionary representing a CSV row

        Returns:
            Project data dictionary
        """
        name = row["Name"]
        repository_url = row["Repository url"]

        # Generate unique filename
        filename = generate_filename(name, repository_url)

        # Generate absolute path for file operations
        absolute_filepath = os.path.join(self.output_dir, filename)

        # Generate relative path from project root for metadata
        relative_filepath = os.path.relpath(absolute_filepath, PROJECT_ROOTDIR)

        # Build base project structure
        project_data = {
            "name": name,
            "category": row["Category"].lower(),
            "country": row["Country"],
            "description": row.get("Description", ""),
            "source": {
                "platform": row["Platform"],
                "url_repository": repository_url,
                "license": row["License"],
                "language": row["Language"],
            },
            "metadata": {
                "filename": filename,
                "filepath": relative_filepath,
                "created_at": get_timestamp(),
            },
        }

        # Add optional documentation URL
        if row.get("Documentation url"):
            project_data["source"]["url_documentation"] = row["Documentation url"]

        # Add owner information
        project_data["owner"] = self._build_owner_data(row)

        return project_data


def main() -> int:
    """Main entry point for import script."""
    parser = argparse.ArgumentParser(
        description="Import entities from CSV to JSON format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import projects from CSV
  python importer.py --csv data.csv --output ./awesome/projects
  # Use default output directory
  python importer.py --csv data.csv
        """,
    )
    parser.add_argument(
        "--csv",
        type=str,
        required=True,
        help="Path to the CSV file with entity data",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=f"{PROJECT_ROOTDIR}/awesome/projects",
        help="Directory to save the JSON files (default: awesome/projects)",
    )

    args = parser.parse_args()

    try:
        print("[INFO] Starting import process...")
        importer = ProjectImporter(args.csv, args.output)
        importer.run()
        print("\n[INFO] ✓ Import completed successfully")
        return 0
    except Exception as e:
        print(f"\n[FATAL] Import failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
