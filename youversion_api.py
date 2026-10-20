import requests

class YouVersionAPI:
    BASE_URL = "https://api.youversion.com/v1"

    @staticmethod
    def get_headers(app_key):
        return {
            "X-YVP-App-Key": app_key,
            "Accept": "application/json"
        }

    @staticmethod
    def get_versions(app_key, lang="en"):
        # The API doesn't seem to natively filter by language in a simple endpoint without auth tokens.
        # But we can try to fetch all bibles and filter client-side, or use ?language_tag=
        url = f"{YouVersionAPI.BASE_URL}/bibles"
        headers = YouVersionAPI.get_headers(app_key)
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            versions = []
            for item in data.get("data", []):
                # Optionally filter by language if the API returns language info
                if item.get("language", {}).get("tag", "").startswith(lang[:2]):
                    versions.append({"id": item["id"], "name": item["abbreviation"] or item["name"]})
            return versions
        except Exception as e:
            print(f"Error fetching versions: {e}")
            return []

    @staticmethod
    def get_passage(app_key, bible_id, reference):
        # Reference should be in format like "JHN.3.16"
        url = f"{YouVersionAPI.BASE_URL}/bibles/{bible_id}/passages/{reference}"
        headers = YouVersionAPI.get_headers(app_key)
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("content", "")
        except Exception as e:
            print(f"Error fetching passage: {e}")
            return None
