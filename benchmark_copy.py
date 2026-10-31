import timeit
from PIL import Image

def benchmark():
    img = Image.new('RGBA', (1080, 1080), color=(73, 109, 137, 255))

    def test_copy():
        return img.copy()

    print("COPY:", timeit.timeit(test_copy, number=1000))

benchmark()
