import timeit
from generator import Generator
from PIL import Image

gen = Generator()
gen.load_locales()

def generate_base_image():
    return gen.generate_image(
        "Português (Brasil)",
        "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.",
        "João 3:16",
        background_filename="default.png"
    )

img = generate_base_image()

def test_lanczos():
    img_copy = img.copy()
    img_copy.thumbnail((500, 500), Image.Resampling.LANCZOS)
    return img_copy

def test_bicubic():
    img_copy = img.copy()
    img_copy.thumbnail((500, 500), Image.Resampling.BICUBIC)
    return img_copy

def test_bilinear():
    img_copy = img.copy()
    img_copy.thumbnail((500, 500), Image.Resampling.BILINEAR)
    return img_copy

print("LANCZOS:", timeit.timeit(test_lanczos, number=100))
print("BICUBIC:", timeit.timeit(test_bicubic, number=100))
print("BILINEAR:", timeit.timeit(test_bilinear, number=100))
