import timeit
import re

setup_original = """
import re
from getbible_api import BOOK_MAPPING
reference = 'João 3:16'
lang = 'pt'

def _original_parse_reference(reference, lang="en"):
    if not reference or len(reference) > 100:
        return None, None, None, None

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
"""

setup_optimized = """
from getbible_api import GetBibleAPI
reference = 'João 3:16'
lang = 'pt'
"""

# Benchmark original implementation
original_time = timeit.timeit(
    "_original_parse_reference(reference, lang)",
    setup=setup_original,
    number=500000
)

# Benchmark optimized implementation
optimized_time = timeit.timeit(
    "GetBibleAPI._parse_reference(reference, lang)",
    setup=setup_optimized,
    number=500000
)

print(f"Original execution time (500k iterations): {original_time:.4f} seconds")
print(f"Optimized execution time (500k iterations): {optimized_time:.4f} seconds")
print(f"Improvement: {((original_time - optimized_time) / original_time) * 100:.2f}%")
