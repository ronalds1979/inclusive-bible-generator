import requests
import re
from book_mapping import BOOK_MAPPING

class GetBibleAPI:
    BASE_URL = "https://api.getbible.net/v2"

    @staticmethod
    def get_versions(lang="en"):
        try:
            versions = []
            lang_prefix = lang[:2].lower()

            if lang_prefix == "pt":
                versions = [
                    {"id": "almeida", "name": "Almeida Atualizada"},
                    {"id": "livre", "name": "Bíblia Livre"}
                ]
            elif lang_prefix == "en":
                versions = [
                    {"id": "web", "name": "World English Bible"},
                    {"id": "kjv", "name": "King James Version"},
                    {"id": "asv", "name": "American Standard Version"},
                    {"id": "bbe", "name": "Bible in Basic English"}
                ]
            elif lang_prefix == "es":
                versions = [
                    {"id": "valera", "name": "Reina Valera (1909)"},
                    {"id": "sse", "name": "Sagradas Escrituras (1569)"}
                ]

            return versions
        except Exception as e:
            print(f"Error fetching versions: {e}")
            return []

    @staticmethod
    def _parse_reference(reference, lang="en"):
        lang_prefix = lang[:2].lower()
        mapping = BOOK_MAPPING.get(lang_prefix, BOOK_MAPPING["en"])

        match = re.match(r'^((?:\d\s+)?[a-zA-ZáéíóúãõçñÁÉÍÓÚÃÕÇÑ\s]+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$', reference.strip())
        if not match:
            return None, None, None, None

        book_name = match.group(1).strip()
        chapter = match.group(2)
        start_verse = match.group(3)
        end_verse = match.group(4)

        book_nr = None
        for k, v in mapping.items():
            if k.lower() == book_name.lower():
                book_nr = v
                break

        return book_nr, chapter, start_verse, end_verse

    @staticmethod
    def get_passage(bible_id, reference, lang="en"):
        book_nr, chapter, start_verse, end_verse = GetBibleAPI._parse_reference(reference, lang)

        if not book_nr or not chapter:
            return None

        url = f"{GetBibleAPI.BASE_URL}/{bible_id}/{book_nr}/{chapter}.json"

        try:
            # SECURITY: Added timeout to prevent thread exhaustion/DoS if API is unresponsive
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            verses = data.get("verses", [])

            if start_verse:
                start_idx = int(start_verse) - 1
                end_idx = int(end_verse) if end_verse else int(start_verse)

                if 0 <= start_idx < len(verses):
                    selected_verses = verses[start_idx:end_idx]
                    return " ".join([v.get("text", "") for v in selected_verses]).strip()
                return None
            else:
                return " ".join([v.get("text", "") for v in verses]).strip()

        except Exception as e:
            print(f"Error fetching passage: {e}")
            return None
