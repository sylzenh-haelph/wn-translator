from pathlib import Path
import json
import os


DB_VERSION = 3


VALID_CHARACTER_TYPES = {
    "character",
}

VALID_PROPER_NOUN_TYPES = {
    "place",
    "organization",
    "item",
    "skill",
    "race",
    "title",
    "proper_noun",
}


def _normalize(text):
    return " ".join(text.casefold().split())


def _empty_db():
    return {
        "version": DB_VERSION,
        "characters": {},
        "proper_nouns": {},
    }


class EntityDB:
    def __init__(self, path="project/entity_db.json"):
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if not self.path.exists():
            data = _empty_db()
            self._save_data(data)
            return data

        with self.path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ValueError(
                "Entity DB harus berupa object JSON."
            )

        version = data.get("version")

        if version not in {1, 2, DB_VERSION}:
            raise ValueError(
                f"Versi Entity DB tidak didukung: {version}"
            )

        data.setdefault("characters", {})
        data.setdefault("proper_nouns", {})

        if version != DB_VERSION:
            self._migrate(data, version)

        return data

    def _migrate(self, data, old_version):
        """
        Migrasi struktur lama ke versi 3.
        """

        for category in (
            "characters",
            "proper_nouns",
        ):
            for record in data[category].values():
                record.setdefault(
                    "research",
                    [],
                )

        # Versi lama tidak menyimpan entity_type
        # secara eksplisit untuk proper_nouns.
        #
        # Karena tipe aslinya sudah hilang pada data lama,
        # kita gunakan proper_noun sebagai fallback.
        for record in data["characters"].values():
            record.setdefault(
                "entity_type",
                "character",
            )

        for record in data["proper_nouns"].values():
            record.setdefault(
                "entity_type",
                "proper_noun",
            )

        data["version"] = DB_VERSION

        self._save_data(data)

    def _save_data(self, data):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = self.path.with_suffix(
            ".tmp"
        )

        with temp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temp_path,
            self.path,
        )

    def save(self):
        self._save_data(self.data)

    def _get_category(self, entity_type):
        if entity_type in VALID_CHARACTER_TYPES:
            return "characters"

        if entity_type in VALID_PROPER_NOUN_TYPES:
            return "proper_nouns"

        raise ValueError(
            f"Entity type tidak didukung: {entity_type}"
        )

    def get(self, text):
        normalized = _normalize(text)

        for category in (
            "characters",
            "proper_nouns",
        ):
            for record in self.data[category].values():

                canonical = _normalize(
                    record.get(
                        "canonical_name",
                        "",
                    )
                )

                if normalized == canonical:
                    return dict(record)

                for alias in record.get(
                    "aliases",
                    [],
                ):
                    if normalized == _normalize(alias):
                        return dict(record)

        return None

    def add(
        self,
        entity_type,
        canonical_name,
        translation=None,
        aliases=None,
        locked=False,
        source="manual",
        notes="",
        research_failed=False,
        research=None,
    ):
        category = self._get_category(
            entity_type
        )

        canonical_name = " ".join(
            canonical_name.split()
        )

        if not canonical_name:
            raise ValueError(
                "canonical_name tidak boleh kosong."
            )

        key = _normalize(
            canonical_name
        )

        if self.get(canonical_name) is not None:
            raise ValueError(
                f"Entity sudah ada: {canonical_name}"
            )

        record = {
            "canonical_name": canonical_name,
            "entity_type": entity_type,
            "translation": translation,
            "aliases": aliases or [],
            "locked": bool(locked),
            "source": source,
            "notes": notes,
            "research_failed": bool(
                research_failed
            ),
            "research": research or [],
        }

        self.data[category][key] = record
        self.save()

        return dict(record)

    def update(
        self,
        entity_type,
        canonical_name,
        **changes,
    ):
        category = self._get_category(
            entity_type
        )

        key = _normalize(
            canonical_name
        )

        if key not in self.data[category]:
            raise KeyError(
                f"Entity tidak ditemukan: "
                f"{canonical_name}"
            )

        record = self.data[category][key]

        allowed_fields = {
            "canonical_name",
            "entity_type",
            "translation",
            "aliases",
            "locked",
            "source",
            "notes",
            "research_failed",
            "research",
        }

        for field, value in changes.items():
            if field in allowed_fields:
                record[field] = value

        self.save()

        return dict(record)

    def add_research(
        self,
        entity_type,
        canonical_name,
        evidence,
    ):
        record = self.get(
            canonical_name
        )

        if record is None:
            return self.add(
                entity_type=entity_type,
                canonical_name=canonical_name,
                source="research",
                research=[evidence],
            )

        category = self._get_category(
            record["entity_type"]
        )

        key = _normalize(
            record["canonical_name"]
        )

        stored_record = self.data[
            category
        ][key]

        stored_record.setdefault(
            "research",
            [],
        )

        stored_record["research"].append(
            evidence
        )

        self.save()

        return dict(stored_record)

    def mark_research_failed(
        self,
        entity_type,
        canonical_name,
    ):
        record = self.get(
            canonical_name
        )

        if record is None:
            return self.add(
                entity_type=entity_type,
                canonical_name=canonical_name,
                source="research",
                research_failed=True,
            )

        category = self._get_category(
            record["entity_type"]
        )

        key = _normalize(
            record["canonical_name"]
        )

        stored_record = self.data[
            category
        ][key]

        stored_record[
            "research_failed"
        ] = True

        self.save()

        return dict(stored_record)

    def list_all(self):
        results = []

        for category in (
            "characters",
            "proper_nouns",
        ):
            for record in self.data[
                category
            ].values():
                results.append(
                    dict(record)
                )

        return results

    def count(self):
        return (
            len(
                self.data["characters"]
            )
            + len(
                self.data["proper_nouns"]
            )
        )
