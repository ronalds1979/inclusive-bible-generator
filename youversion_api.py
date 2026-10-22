import requests

class YouVersionAPI:
    # Switching to bible-api.com since YouVersion API keys are problematic
    BASE_URL = "https://bible-api.com"

    @staticmethod
    def get_versions(app_key=None, lang="en"):
        try:
            versions = []
            lang_prefix = lang[:2].lower()

            # bible-api.com supports some specific translations natively
            if lang_prefix == "pt":
                versions = [{"id": "almeida", "name": "João Ferreira de Almeida"}]
            elif lang_prefix == "en":
                versions = [
                    {"id": "web", "name": "World English Bible"},
                    {"id": "kjv", "name": "King James Version"},
                    {"id": "asv", "name": "American Standard Version"},
                    {"id": "bbe", "name": "Bible in Basic English"},
                    {"id": "darby", "name": "Darby Bible"}
                ]
            elif lang_prefix == "es":
                # Currently no official ES support in bible-api.com, falling back to manual text entry
                pass

            return versions
        except Exception as e:
            print(f"Error fetching versions: {e}")
            return []

    @staticmethod
    def get_passage(app_key, bible_id, reference):
        url = f"{YouVersionAPI.BASE_URL}/{reference}?translation={bible_id}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("text", "").strip()
        except Exception as e:
            print(f"Error fetching passage: {e}")
            return None
