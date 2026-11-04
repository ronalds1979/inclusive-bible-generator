import timeit
import requests
import getbible_api

# Without session
def without_session():
    requests.get("https://api.getbible.net/v2/web/43/3.json", timeout=10)

# With session
session = requests.Session()
def with_session():
    session.get("https://api.getbible.net/v2/web/43/3.json", timeout=10)

if __name__ == "__main__":
    print("Without session:", timeit.timeit(without_session, number=10))
    print("With session:", timeit.timeit(with_session, number=10))
