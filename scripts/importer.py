import argparse
import csv
import hashlib
import json
import os
import sys
import unicodedata
from datetime import UTC, datetime

from validator import ProjectValidator, Validator


PROJCET_ROOTDIR = os.path.dirname(os.path.abspath(__file__).replace("scripts/", ""))


class Importer:
    def __init__(self, csv_filepath: str, output_dir: str, validator: Validator):
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

    def load_csv(self):
        print(f"[INFO] Loading data from {self.csv_filepath}")
        if not os.path.exists(self.csv_filepath):
            raise FileNotFoundError(f"CSV file not found: {self.csv_filepath}")

        with open(self.csv_filepath, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return list(reader)

    def execute(self):
        raise NotImplementedError(
            "The process method must be implemented in the subclass"
        )

    def run(self):
        self.execute()
        print(self.validator)


class ProjectImporter(Importer):
    def __init__(self, csv_filepath: str, output_dir: str):
        super().__init__(csv_filepath, output_dir, ProjectValidator())

    def execute(self):
        data = self.load_csv()

        for row in data:
            name = row["Name"]

            normalized_name = (
                "".join(
                    c
                    for c in unicodedata.normalize("NFD", name)
                    if unicodedata.category(c) != "Mn"
                )
                .replace(" ", "-")
                .lower()
            )
            unique_string = f"{normalized_name}:{row['Repository url']}"

            filename = f"{normalized_name}-{hashlib.sha256(unique_string.encode()).hexdigest()[0:6]}.json"
            print(f"  [INFO] Filename: {filename}")

            filepath = os.path.join(self.output_dir, filename)

            project_data = {
                "name": name,
                "category": row["Category"].lower(),
                "country": row["Country"],
                "description": row.get("Description", ""),
                "source": {
                    "platform": row["Platform"],
                    "url_repository": row["Repository url"],
                    "license": row["License"],
                    "language": row["Language"],
                },
                "metadata": {
                    "filename": filename,
                    "filepath": filepath,
                    "created_at": str(datetime.now(UTC).isoformat()[:-13] + "Z"),
                },
            }

            if row.get("Documentation url", ""):
                project_data["source"]["url_documentation"] = row["Documentation url"]

            if row["Who is the owner of this project?"] == "Company":
                project_data["owner"] = {
                    "type": "company",
                    "name": row["Company Name"],
                    "url_website": row["Company Website"],
                    "is_a_startup": row["Your company is a Startup?"],
                    **(
                        {
                            "description": row["Company Description"],
                        }
                        if row.get("Company Description", "")
                        else {}
                    ),
                }
            if row["Who is the owner of this project?"] == "Individual":
                project_data["owner"] = {
                    "type": "individual",
                    "name": row["Owner Full Name or Username"],
                }
            if row["Who is the owner of this project?"] == "Community":
                project_data["owner"] = {
                    "type": "community",
                    "name": row["Community Name"],
                    "url_website": row["Community Website"],
                    **(
                        {
                            "description": row["Community Description"],
                        }
                        if row.get("Community Description", "")
                        else {}
                    ),
                }

            try:
                project_data, err = self.validator.validate(data=project_data)

                if err:
                    sys.tracebacklimit = 0
                    raise Exception()

                with open(filepath, mode="w", encoding="utf-8") as json_file:
                    json.dump(project_data, json_file, indent=2)

                print(f"  [INFO] Created {name} project")
            except Exception as e:
                raise e


def main():
    parser = argparse.ArgumentParser(description="Import projects from CSV")
    parser.add_argument(
        "--csv",
        type=str,
        required=True,
        help="Path to the CSV file with project data",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=f"{PROJCET_ROOTDIR}/awesome/projects",
        help="Directory to save the JSON files",
    )
    args = parser.parse_args()

    project = ProjectImporter(args.csv, args.output)
    project.run()


if __name__ == "__main__":
    sys.exit(main())
