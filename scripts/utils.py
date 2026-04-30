import hashlib
import re
import unicodedata
from datetime import UTC, datetime


def sanitize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value))

    # handle both escaped sequences (e.g. from CSV) and real control chars
    normalized = (
        normalized.replace("\\t", " ")
        .replace("\\n", " ")
        .replace("\\r", " ")
        .replace("\t", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )

    normalized = "".join(
        char for char in normalized if unicodedata.category(char)[0] != "C"
    )

    return re.sub(r"\s+", " ", normalized).strip()


def sanitize_name(value: str) -> str:
    normalized = sanitize_text(value)
    normalized = re.sub(r"[^\w\s\-\.'&]", "", normalized, flags=re.UNICODE)
    return re.sub(r"\s+", " ", normalized).strip()


def sanitize_description(value: str) -> str:
    normalized = sanitize_text(value)
    normalized = re.sub(
        r"[^\w\s\-\.,;:!?()'\"/&]",
        "",
        normalized,
        flags=re.UNICODE,
    )
    return re.sub(r"\s+", " ", normalized).strip()


def normalize_name(name: str) -> str:
    normalized_name = sanitize_name(name)

    # NFD decomposition strips combining marks (accents) without losing base letters
    name_without_accents = "".join(
        c
        for c in unicodedata.normalize("NFD", normalized_name)
        if unicodedata.category(c) != "Mn"
    )

    slug_base = re.sub(r"[^a-zA-Z0-9\s-]", "", name_without_accents)
    slug_base = re.sub(r"[\s_-]+", "-", slug_base).strip("-")

    if not slug_base:
        return "entity"

    return slug_base.lower()


def generate_filename(name: str, unique_identifier: str) -> str:
    normalized_name = normalize_name(name)
    unique_string = f"{normalized_name}:{unique_identifier}"
    hash_suffix = hashlib.sha256(unique_string.encode()).hexdigest()[:6]
    return f"{normalized_name}-{hash_suffix}.json"


def get_timestamp() -> str:
    return datetime.now(UTC).isoformat()[:-13] + "Z"
