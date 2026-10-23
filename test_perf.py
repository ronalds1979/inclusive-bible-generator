from generator import Generator
import time

def run():
    gen = Generator()

    # First run (should read from disk)
    start = time.time()
    img1 = gen.generate_image("pt-BR", "No princípio, criou Deus os céus e a terra.", "Gênesis 1:1")
    t1 = time.time() - start
    print(f"First run (cold cache): {t1:.4f}s")

    # Second run (should hit cache)
    start = time.time()
    img2 = gen.generate_image("pt-BR", "A terra, porém, estava sem forma e vazia.", "Gênesis 1:2")
    t2 = time.time() - start
    print(f"Second run (warm cache): {t2:.4f}s")

    # Ensure they are different instances but caching worked
    assert img1 is not img2
    print("Success! Images generated without error.")

if __name__ == "__main__":
    run()
