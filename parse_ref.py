import re

USFM_MAP = {
    "gen": "GEN", "genesis": "GEN", "gênesis": "GEN",
    "exo": "EXO", "exodus": "EXO", "êxodo": "EXO", "exodo": "EXO",
    "lev": "LEV", "leviticus": "LEV", "levítico": "LEV", "levitico": "LEV",
    "num": "NUM", "numbers": "NUM", "números": "NUM", "numeros": "NUM",
    "deut": "DEU", "deuteronomy": "DEU", "deuteronômio": "DEU", "deuteronomio": "DEU",
    "jos": "JOS", "joshua": "JOS", "josué": "JOS", "josue": "JOS",
    "judg": "JDG", "judges": "JDG", "juízes": "JDG", "juizes": "JDG", "jueces": "JDG",
    "ruth": "RUT", "rute": "RUT", "rut": "RUT",
    "1 samuel": "1SA", "1samuel": "1SA", "i samuel": "1SA", "1sam": "1SA",
    "2 samuel": "2SA", "2samuel": "2SA", "ii samuel": "2SA", "2sam": "2SA",
    "1 reis": "1KI", "1reis": "1KI", "1 kings": "1KI", "1kings": "1KI", "1 reyes": "1KI", "1reyes": "1KI", "1kgs": "1KI",
    "2 reis": "2KI", "2reis": "2KI", "2 kings": "2KI", "2kings": "2KI", "2 reyes": "2KI", "2reyes": "2KI", "2kgs": "2KI",
    "1 crônicas": "1CH", "1crônicas": "1CH", "1 cronicas": "1CH", "1 chronicles": "1CH", "1 crónicas": "1CH", "1chr": "1CH",
    "2 crônicas": "2CH", "2crônicas": "2CH", "2 cronicas": "2CH", "2 chronicles": "2CH", "2 crónicas": "2CH", "2chr": "2CH",
    "esdras": "EZR", "ezra": "EZR",
    "neemias": "NEH", "nehemiah": "NEH", "neh": "NEH",
    "ester": "EST", "esther": "EST", "esth": "EST",
    "jó": "JOB", "jo": "JOB", "job": "JOB",
    "salmos": "PSA", "salmo": "PSA", "psalms": "PSA", "psalm": "PSA", "ps": "PSA",
    "provérbios": "PRO", "proverbios": "PRO", "proverbs": "PRO", "prov": "PRO",
    "eclesiastes": "ECC", "ecclesiastes": "ECC", "eclesiastés": "ECC", "eccl": "ECC",
    "cantares": "SNG", "cantares de salomão": "SNG", "cantares de salomón": "SNG", "cânticos": "SNG", "canticos": "SNG", "song of solomon": "SNG", "song": "SNG",
    "isaías": "ISA", "isaias": "ISA", "isaiah": "ISA", "isa": "ISA",
    "jeremias": "JER", "jeremiah": "JER", "jer": "JER",
    "lamentações": "LAM", "lamentaciones": "LAM", "lamentations": "LAM", "lam": "LAM",
    "ezequiel": "EZK", "ezekiel": "EZK", "ezek": "EZK",
    "daniel": "DAN", "dan": "DAN",
    "oséias": "HOS", "oseas": "HOS", "hosea": "HOS", "hos": "HOS",
    "joel": "JOL",
    "amós": "AMO", "amos": "AMO",
    "obadias": "OBA", "abdías": "OBA", "abdias": "OBA", "obadiah": "OBA", "obad": "OBA",
    "jonas": "JON", "jonah": "JON", "jon": "JON",
    "miquéias": "MIC", "miqueas": "MIC", "micah": "MIC", "mic": "MIC",
    "naum": "NAM", "nahúm": "NAM", "nahum": "NAM", "nah": "NAM",
    "habacuque": "HAB", "habacuc": "HAB", "habakkuk": "HAB", "hab": "HAB",
    "sofonias": "ZEP", "sofonías": "ZEP", "zephaniah": "ZEP", "zeph": "ZEP",
    "ageu": "HAG", "hageo": "HAG", "haggai": "HAG", "hag": "HAG",
    "zacarias": "ZEC", "zacarías": "ZEC", "zechariah": "ZEC", "zech": "ZEC",
    "malaquias": "MAL", "malaquías": "MAL", "malachi": "MAL", "mal": "MAL",
    "mateus": "MAT", "mateo": "MAT", "matthew": "MAT", "matt": "MAT",
    "marcos": "MRK", "mark": "MRK",
    "lucas": "LUK", "luke": "LUK",
    "joão": "JHN", "joao": "JHN", "juan": "JHN", "john": "JHN",
    "atos": "ACT", "hechos": "ACT", "acts": "ACT",
    "romanos": "ROM", "romans": "ROM", "rom": "ROM",
    "1 coríntios": "1CO", "1coríntios": "1CO", "1 corintios": "1CO", "1 corinthians": "1CO", "1cor": "1CO",
    "2 coríntios": "2CO", "2coríntios": "2CO", "2 corintios": "2CO", "2 corinthians": "2CO", "2cor": "2CO",
    "gálatas": "GAL", "galatas": "GAL", "galatians": "GAL", "gal": "GAL",
    "efésios": "EPH", "efesios": "EPH", "ephesians": "EPH", "eph": "EPH",
    "filipenses": "PHP", "philippians": "PHP", "phil": "PHP",
    "colossenses": "COL", "colosenses": "COL", "colossians": "COL", "col": "COL",
    "1 tessalonicenses": "1TH", "1tessalonicenses": "1TH", "1 thessalonians": "1TH", "1thess": "1TH",
    "2 tessalonicenses": "2TH", "2tessalonicenses": "2TH", "2 thessalonians": "2TH", "2thess": "2TH",
    "1 timóteo": "1TI", "1timóteo": "1TI", "1 timoteo": "1TI", "1 timothy": "1TI", "1tim": "1TI",
    "2 timóteo": "2TI", "2timóteo": "2TI", "2 timoteo": "2TI", "2 timothy": "2TI", "2tim": "2TI",
    "tito": "TIT", "titus": "TIT",
    "filemom": "PHM", "filemón": "PHM", "filemon": "PHM", "philemon": "PHM", "philem": "PHM",
    "hebreus": "HEB", "hebreos": "HEB", "hebrews": "HEB", "heb": "HEB",
    "tiago": "JAS", "santiago": "JAS", "james": "JAS", "jas": "JAS",
    "1 pedro": "1PE", "1pedro": "1PE", "1 peter": "1PE", "1pet": "1PE",
    "2 pedro": "2PE", "2pedro": "2PE", "2 peter": "2PE", "2pet": "2PE",
    "1 joão": "1JN", "1 joao": "1JN", "1joão": "1JN", "1 juan": "1JN", "1 john": "1JN", "1john": "1JN",
    "2 joão": "2JN", "2 joao": "2JN", "2joão": "2JN", "2 juan": "2JN", "2 john": "2JN", "2john": "2JN",
    "3 joão": "3JN", "3 joao": "3JN", "3joão": "3JN", "3 juan": "3JN", "3 john": "3JN", "3john": "3JN",
    "judas": "JUD", "jude": "JUD",
    "apocalipse": "REV", "apocalipsis": "REV", "revelation": "REV", "rev": "REV"
}

def parse_reference(ref_str):
    # Try to extract book, chapter, verse. Handles numbers at start too.
    match = re.match(r"^(\d?\s*[a-zA-ZáéíóúãõâêîôûçñÁÉÍÓÚÃÕÂÊÎÔÛÇÑ]+)\s+(\d+)[:\.](\d+)", ref_str.strip())
    if match:
        book_str = match.group(1).lower().strip()
        book_str = re.sub(r'\s+', ' ', book_str)
        chapter = match.group(2)
        verse = match.group(3)

        book_usfm = USFM_MAP.get(book_str)
        if book_usfm:
            return f"{book_usfm}.{chapter}.{verse}"
    return ref_str
