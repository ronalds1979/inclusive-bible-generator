import sys
from youversion_api import YouVersionAPI

key = "dummy"
print("Testing versions...")
res = YouVersionAPI.get_versions(key, "pt")
print(res)
