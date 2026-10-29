import timeit
from getbible_api import GetBibleAPI

def run_benchmark():
    setup_code = """
from getbible_api import GetBibleAPI
reference = 'John 3:16-18'
"""
    test_code = """
GetBibleAPI._parse_reference(reference)
"""

    # Run the test 100,000 times
    number_of_executions = 100000

    time_taken = timeit.timeit(stmt=test_code, setup=setup_code, number=number_of_executions)
    print(f"Time taken for {number_of_executions} executions: {time_taken:.6f} seconds")

if __name__ == "__main__":
    run_benchmark()
