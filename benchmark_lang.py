import timeit

def test_replace():
    lang = "Português (Brasil)"
    return lang.replace(" (Brasil)", "").replace("English (US/UK)", "en").replace("Español (España)", "es").replace("Português", "pt-BR")

LANG_MAP = {
    "Português (Brasil)": "pt-BR",
    "English (US/UK)": "en",
    "Español (España)": "es",
    "Português": "pt-BR"
}
def test_dict():
    lang = "Português (Brasil)"
    return LANG_MAP.get(lang, lang)

print("Replace:", timeit.timeit(test_replace, number=1000000))
print("Dict:", timeit.timeit(test_dict, number=1000000))
