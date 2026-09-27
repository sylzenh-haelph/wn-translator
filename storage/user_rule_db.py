import json
from pathlib import Path


DB_VERSION = 1


def _normalize_rule_id(rule_id):
    return str(rule_id).strip()


class UserRuleDB:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self._load()

    def _empty_db(self):
        return {
            "version": DB_VERSION,
            "rules": {},
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

        if "rules" not in data:
            data["rules"] = {}

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
        rule_id,
        rule_type,
        target,
        value,
        locked=False,
        notes="",
        context="",
    ):
        rule_id = _normalize_rule_id(rule_id)

        if rule_id in self.data["rules"]:
            raise KeyError(
                f"Rule ID sudah ada: {rule_id}"
            )

        record = {
            "rule_id": rule_id,
            "rule_type": rule_type,
            "target": target,
            "value": value,
            "locked": bool(locked),
            "notes": notes,
            "context": context,
        }

        self.data["rules"][rule_id] = record
        self._save()

        return record.copy()

    def get(self, rule_id):
        rule_id = _normalize_rule_id(rule_id)

        record = self.data["rules"].get(rule_id)

        if record is None:
            return None

        return record.copy()

    def update(
        self,
        rule_id,
        **changes,
    ):
        rule_id = _normalize_rule_id(rule_id)

        if rule_id not in self.data["rules"]:
            raise KeyError(
                f"Rule tidak ditemukan: {rule_id}"
            )

        allowed_fields = {
            "rule_type",
            "target",
            "value",
            "locked",
            "notes",
            "context",
        }

        record = self.data["rules"][rule_id]

        for field, value in changes.items():
            if field not in allowed_fields:
                raise ValueError(
                    f"Field tidak boleh diubah: {field}"
                )

            record[field] = value

        self._save()

        return record.copy()

    def remove(self, rule_id):
        rule_id = _normalize_rule_id(rule_id)

        if rule_id not in self.data["rules"]:
            return False

        del self.data["rules"][rule_id]
        self._save()

        return True

    def lock(self, rule_id):
        rule_id = _normalize_rule_id(rule_id)

        if rule_id not in self.data["rules"]:
            raise KeyError(
                f"Rule tidak ditemukan: {rule_id}"
            )

        record = self.data["rules"][rule_id]
        record["locked"] = True

        self._save()

        return record.copy()

    def unlock(self, rule_id):
        rule_id = _normalize_rule_id(rule_id)

        if rule_id not in self.data["rules"]:
            raise KeyError(
                f"Rule tidak ditemukan: {rule_id}"
            )

        record = self.data["rules"][rule_id]
        record["locked"] = False

        self._save()

        return record.copy()

    def find_by_target(self, target):
        target_normalized = target.strip().casefold()

        results = []

        for record in self.data["rules"].values():
            stored_target = str(
                record.get("target", "")
            ).strip().casefold()

            if stored_target == target_normalized:
                results.append(record.copy())

        return results

    def list_all(self):
        return [
            record.copy()
            for record in self.data["rules"].values()
        ]

    def count(self):
        return len(self.data["rules"])
