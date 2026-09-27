import json
from pathlib import Path


DB_VERSION = 1


def _normalize(term):
    return term.strip().casefold()


class GlossaryDB:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self._load()

    def _empty_db(self):
        return {
            "version": DB_VERSION,
            "terms": {},
        }

    def _load(self):
        if not self.path.exists():
            return self._empty_db()

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if "version" not in data:
            data["version"] = DB_VERSION

        if "terms" not in data:
            data["terms"] = {}

        return data

    def _save(self):
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )

        with temp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.data,
                file,
                ensure_ascii=False,
                indent=2,
            )

        temp_path.replace(self.path)

    def add(
        self,
        term,
        translation=None,
        aliases=None,
        locked=False,
        source="user",
        notes="",
        context="",
        case_sensitive=False,
    ):
        key = _normalize(term)

        if key in self.data["terms"]:
            raise KeyError(
                f"Glossary term sudah ada: {term}"
            )

        record = {
            "term": term,
            "translation": translation,
            "aliases": aliases or [],
            "locked": bool(locked),
            "source": source,
            "notes": notes,
            "context": context,
            "case_sensitive": bool(
                case_sensitive
            ),
        }

        self.data["terms"][key] = record
        self._save()

        return record

    def get(self, term):
        key = _normalize(term)

        record = self.data["terms"].get(key)

        if record is None:
            return None

        return record.copy()

    def update(
        self,
        term,
        **changes,
    ):
        key = _normalize(term)

        if key not in self.data["terms"]:
            raise KeyError(
                f"Glossary term tidak ditemukan: {term}"
            )

        allowed_fields = {
            "term",
            "translation",
            "aliases",
            "locked",
            "source",
            "notes",
            "context",
            "case_sensitive",
        }

        record = self.data["terms"][key]

        for field, value in changes.items():
            if field not in allowed_fields:
                raise ValueError(
                    f"Field tidak boleh diubah: {field}"
                )

            record[field] = value

        self._save()

        return record.copy()

    def remove(self, term):
        key = _normalize(term)

        if key not in self.data["terms"]:
            return False

        del self.data["terms"][key]
        self._save()

        return True

    def add_alias(
        self,
        term,
        alias,
    ):
        key = _normalize(term)

        if key not in self.data["terms"]:
            raise KeyError(
                f"Glossary term tidak ditemukan: {term}"
            )

        record = self.data["terms"][key]

        if alias not in record["aliases"]:
            record["aliases"].append(alias)

        self._save()

        return record.copy()

    def find_by_alias(self, alias):
        alias_key = _normalize(alias)

        for record in self.data["terms"].values():
            for stored_alias in record.get(
                "aliases",
                [],
            ):
                if (
                    _normalize(stored_alias)
                    == alias_key
                ):
                    return record.copy()

        return None

    def resolve(self, term):
        """
        Cari berdasarkan:
        1. canonical term
        2. alias

        Mengembalikan record glossary.
        """
        record = self.get(term)

        if record is not None:
            return record

        return self.find_by_alias(term)

    def lock(
        self,
        term,
        translation=None,
    ):
        key = _normalize(term)

        if key not in self.data["terms"]:
            raise KeyError(
                f"Glossary term tidak ditemukan: {term}"
            )

        record = self.data["terms"][key]

        if translation is not None:
            record["translation"] = translation

        record["locked"] = True

        self._save()

        return record.copy()

    def unlock(self, term):
        key = _normalize(term)

        if key not in self.data["terms"]:
            raise KeyError(
                f"Glossary term tidak ditemukan: {term}"
            )

        record = self.data["terms"][key]
        record["locked"] = False

        self._save()

        return record.copy()

    def list_all(self):
        return [
            record.copy()
            for record in self.data["terms"].values()
        ]

    def count(self):
        return len(self.data["terms"])
