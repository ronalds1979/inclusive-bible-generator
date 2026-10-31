import timeit
from generator import Generator

gen = Generator()
gen.load_locales()

def test_generate():
    return gen.generate_image(
        "Português (Brasil)",
        "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.",
        "João 3:16",
        background_filename="default.png"
    )

def test_generate_and_lanczos():
    img = test_generate()
    img.thumbnail((500, 500), __import__('PIL').Image.Resampling.LANCZOS)
    return img

def test_generate_and_bilinear():
    img = test_generate()
    img.thumbnail((500, 500), __import__('PIL').Image.Resampling.BILINEAR)
    return img

print("Generate only:", timeit.timeit(test_generate, number=100))
print("Generate + Lanczos:", timeit.timeit(test_generate_and_lanczos, number=100))
print("Generate + Bilinear:", timeit.timeit(test_generate_and_bilinear, number=100))
