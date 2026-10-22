from youversion_api import YouVersionAPI

text = YouVersionAPI.get_passage(None, 'web', 'John 3:16')
print(f"Text fetched: {text[:50]}...")
if text and "God so loved" in text:
    print("Test passed!")
else:
    print("Test failed!")
