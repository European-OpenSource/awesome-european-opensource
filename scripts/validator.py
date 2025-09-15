import json
import os
import sys

import fastjsonschema


PROJCET_ROOTDIR = os.path.dirname(os.path.abspath(__file__).replace("scripts/", ""))


def get_jsonschema(nane: str):
    with open(f"{PROJCET_ROOTDIR}/schemas/{nane}.json") as f:
        return json.load(f)


class Validator:
    schema_name = None
    schema_configuration = None
    source_filepath = None
    source_data = {}
    metadata = {
        "success": 0,
        "failed": 0,
        "warning": 0,
        "total": 0,
        "errors": [],
    }

    def __init__(self) -> None:
        self.schema_configuration = fastjsonschema.compile(
            definition=get_jsonschema(self.schema_name)
        )

    def save_state(self, name: str, error: str, key: str = "failed"):
        self.metadata[key] += 1
        self.metadata["errors"].append(
            {
                "name": name,
                "message": error,
            }
        )

    def validate(self, filename: str = None, data: dict = None):
        if not filename and not data:
            raise Exception("You must provide a filename or data")

        if filename:
            if not os.path.isfile(filename):
                print(f"  [WARN] Not found {os.path.basename(filename)}")
                self.save_state(filename, f"File not found {filename}", "warning")
                return {}
            with open(filename) as f:
                data = json.load(f)

        try:
            print(f"  [VALIDATE] {data['name']}")
            self.schema_configuration(data)

            if os.path.isfile(data["metadata"]["filepath"]):
                print(
                    f"  [WARN] Project {data['name']} already exists. File: {data['metadata']['filename']}"
                )
                self.save_state(
                    data["name"],
                    f"Project {data['name']} already exists. File: {data['metadata']['filename']}",
                    "warning",
                )
                return data, None

            self.metadata["success"] += 1
            return data, None
        except fastjsonschema.JsonSchemaException as e:
            print(f"  [ERROR] {data['name']} - {e.message}")
            self.save_state(data["name"], e.message)
            return None, self.metadata["errors"]
        except json.JSONDecodeError as e:
            print(f"  [ERROR] {data['name']} - {e.msg}")
            self.save_state(data["name"], e.msg)
            return None, self.metadata["errors"]
        except Exception as e:
            print(f"  [ERROR] {data['name']} - {e}")
            self.save_state(data["name"], str(e))
            return None, self.metadata["errors"]
        finally:
            self.metadata["total"] += 1

    def execute(self, dirpath: str):
        print(f"[INFO] Validate {dirpath} directory")

        if not os.path.isdir(dirpath):
            raise NotADirectoryError(dirpath)

        loaded_files = []
        for project in os.listdir(dirpath):
            filename = os.path.join(dirpath, project)

            if not os.path.isfile(filename):
                print(f"  [WARN] Not found {os.path.basename(filename)}")
                self.save_state(filename, f"File not found {filename}", "warning")
                continue

            if not project.endswith(".json"):
                print(
                    f"  [WARN] Invalid file {os.path.basename(filename)} must be .json"
                )
                self.save_state(
                    filename, f"Invalid file {filename} must be .json", "warning"
                )
                continue

            item = (project.replace(".json", ""), filename)

            loaded_files.append(item)

        for name, filename in sorted(loaded_files, key=lambda tupla: tupla[0]):
            self.source_data[name], _ = self.validate(filename)

        return self.source_data

    def print(self):
        print(f"[INFO] Scanned {self.metadata['total']} projects")
        print(f"[INFO] Success {self.metadata['success']} projects")
        print(f"[INFO] Failed {self.metadata['failed']} projects")
        if len(self.metadata["errors"]) > 0:
            print("[INFO] Errors:")
            for error in self.metadata["errors"]:
                print(f"  - {error['name']} - {error['message']}")
        else:
            print("[INFO] No errors found")

    def run(self):
        if self.schema_name is None:
            raise NotImplementedError("schema_name is not defined")

        if self.source_filepath is None:
            raise NotImplementedError("source_filepath is not defined")

        self.execute(self.source_filepath)
        self.print()

    def raise_on_error(self):
        sys.tracebacklimit = 0
        if self.metadata["failed"] > 0:
            raise Exception("Validation failed")

    @property
    def data(self):
        return self.source_data

    def __str__(self):
        return f"Validator: {self.metadata}"


class ProjectValidator(Validator):
    schema_name = "project"
    source_filepath = f"{PROJCET_ROOTDIR}/awesome/projects"


def main():
    projects = ProjectValidator()
    projects.run()
    projects.raise_on_error()


if __name__ == "__main__":
    sys.exit(main())
