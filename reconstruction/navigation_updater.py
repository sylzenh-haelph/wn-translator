from bs4 import BeautifulSoup


class NavigationUpdater:
    """
    Memperbarui label link pada EPUB nav.xhtml
    berdasarkan mapping href -> judul baru.

    Struktur nav asli dipertahankan.
    Hanya text label <a> yang diubah.
    """

    def update(
        self,
        html,
        href_to_title,
    ):
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        for link in soup.find_all("a"):
            href = link.get("href")

            if not href:
                continue

            if href not in href_to_title:
                continue

            link.clear()
            link.append(
                href_to_title[href]
            )

        return str(soup)


def update_navigation(
    html,
    href_to_title,
):
    return NavigationUpdater().update(
        html,
        href_to_title,
    )
