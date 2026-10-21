import requests

def test_api():
    url = "https://api.youversion.com/v1/bibles"
    headers = {"x-youversion-developer-token": "dummy"}
    try:
        response = requests.get(url, headers=headers)
        print(response.status_code)
        print(response.text)
    except Exception as e:
        print(e)

test_api()
