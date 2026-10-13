from typing import Callable


class FailoverModelClient:
    """
    Mencoba model dalam urutan yang sudah ditentukan.

    Setiap client sudah melakukan retry sendiri untuk error sementara.
    Wrapper ini hanya pindah ke cadangan setelah client gagal sepenuhnya,
    dan mencatat label model yang akhirnya melayani request.
    """

    def __init__(
        self,
        clients,
        labels=None,
        on_failover: Callable | None = None,
    ):
        if not clients:
            raise ValueError("clients tidak boleh kosong.")

        self.clients = list(clients)
        self.labels = (
            list(labels)
            if labels is not None
            else [f"model_{index}" for index in range(len(self.clients))]
        )

        if len(self.labels) != len(self.clients):
            raise ValueError("labels harus sama panjang dengan clients.")

        self.on_failover = on_failover
        self.last_used = None

    def generate(self, prompt):
        errors = []

        for index, client in enumerate(self.clients):
            label = self.labels[index]

            try:
                text = client.generate(prompt)
            except (RuntimeError, OSError) as exc:
                errors.append(f"{label}: {exc}")

                if self.on_failover and index + 1 < len(self.clients):
                    self.on_failover(label, exc)

                continue

            self.last_used = label
            return text

        raise RuntimeError(
            "Semua model gagal: " + " | ".join(errors)
        )
