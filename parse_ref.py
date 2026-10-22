def process_reference_for_audio(reference, lang_code):
    import re
    # Convert "João 3:16" to "João, capítulo 3, versículo 16"
    match = re.match(r"^([^\d]+|\d?\s*[a-zA-ZáéíóúãõâêîôûçñÁÉÍÓÚÃÕÂÊÎÔÛÇÑ]+)\s+(\d+)[:\.](\d+)", reference.strip())
    if match:
        book = match.group(1).strip()
        chapter = match.group(2)
        verse = match.group(3)

        if lang_code == "pt-BR":
            return f"{book}, capítulo {chapter}, versículo {verse}"
        elif lang_code == "es":
            return f"{book}, capítulo {chapter}, versículo {verse}"
        else: # en
            return f"{book}, chapter {chapter}, verse {verse}"
    return reference
print(process_reference_for_audio("João 3:16", "pt-BR"))
print(process_reference_for_audio("1 João 3:16", "pt-BR"))
