import os
import tempfile
import time
import unittest
from unittest.mock import patch
from PIL import Image

from generator import Generator
from getbible_api import GetBibleAPI


class TestSecurity(unittest.TestCase):
    def setUp(self):
        self.generator = Generator()

    def test_parse_reference_supports_circumflex_and_accents(self):
        book_nr, chapter, start_v, end_v = GetBibleAPI._parse_reference("Gênesis 1:1", lang="pt")
        self.assertEqual((book_nr, chapter, start_v, end_v), (1, "1", "1", None))

        book_nr, chapter, start_v, end_v = GetBibleAPI._parse_reference("Êxodo 20:1-3", lang="pt")
        self.assertEqual((book_nr, chapter, start_v, end_v), (2, "20", "1", "3"))

        book_nr, chapter, start_v, end_v = GetBibleAPI._parse_reference("1 Coríntios 13:4-7", lang="pt")
        self.assertEqual((book_nr, chapter, start_v, end_v), (46, "13", "4", "7"))

    def test_parse_reference_no_redos_and_bounds(self):
        # Oversized reference rejected early
        self.assertEqual(GetBibleAPI._parse_reference("João " + "a" * 120 + " 3:16", lang="pt"), (None, None, None, None))

        # Pathological whitespace string should finish virtually instantaneously (no catastrophic backtracking)
        evil = "1 " + " ".join(["word"] * 25) + "!"
        start = time.monotonic()
        res = GetBibleAPI._parse_reference(evil, lang="en")
        elapsed = time.monotonic() - start
        self.assertEqual(res, (None, None, None, None))
        self.assertLess(elapsed, 0.2)

    def test_get_passage_rejects_inverted_range(self):
        with patch.object(GetBibleAPI, "_fetch_chapter", return_value=("In the beginning", "And the earth", "And God said", "And God saw", "And God called")):
            self.assertIsNone(GetBibleAPI.get_passage("web", "Genesis 1:5-3", lang="en"))
            self.assertEqual(GetBibleAPI.get_passage("web", "Genesis 1:1-2", lang="en"), "In the beginning And the earth")

    def test_sanitize_filename_blocks_path_traversal(self):
        for payload in ["../../etc/passwd", r"..\Windows\System32\cmd.exe", "", "   ///   "]:
            cleaned = Generator.sanitize_filename(payload)
            self.assertNotIn("/", cleaned)
            self.assertNotIn("\\", cleaned)
            self.assertNotIn("..", cleaned)
            self.assertTrue(len(cleaned) > 0)

    def test_is_safe_regular_file_rejects_device_names_and_symlinks(self):
        self.assertFalse(Generator._is_safe_regular_file("CON"))
        self.assertFalse(Generator._is_safe_regular_file("NUL.png"))
        self.assertFalse(Generator._is_safe_regular_file("CON .png"))
        self.assertFalse(Generator._is_safe_regular_file("CON.tar.png"))
        self.assertFalse(Generator._is_safe_regular_file("verse.png:ads"))
        self.assertFalse(Generator._is_safe_regular_file(r"\\.\C:\file.png"))
        self.assertFalse(Generator._is_safe_regular_file(r"\\?\C:\file.png"))
        self.assertFalse(Generator._is_safe_regular_file("//./pipe/test.png"))

        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = os.path.join(tmpdir, "empty.png")
            with open(empty_file, "wb"):
                pass
            self.assertFalse(Generator._is_safe_regular_file(empty_file))

            valid_file = os.path.join(tmpdir, "valid.png")
            with open(valid_file, "wb") as f:
                f.write(b"1234")
            self.assertTrue(Generator._is_safe_regular_file(valid_file))

            link_path = os.path.join(tmpdir, "link.png")
            try:
                os.symlink(valid_file, link_path)
            except (OSError, NotImplementedError):
                # Symlink creation may require Developer Mode / elevation on Windows; mock _is_reparse_point
                with patch.object(Generator, "_is_reparse_point", side_effect=lambda p: p == os.path.abspath(valid_file)):
                    self.assertFalse(Generator._is_safe_regular_file(valid_file))
            else:
                self.assertFalse(Generator._is_safe_regular_file(link_path))

    def test_save_image_atomic_writes_png_and_rejects_unsafe_paths(self):
        img = Image.new("RGB", (32, 32), color=(10, 20, 30))
        with self.assertRaises(ValueError):
            self.generator.save_image_atomic(img, "CON.png")
        with self.assertRaises(ValueError):
            self.generator.save_image_atomic(img, r"\\.\pipe\test.png")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "verse.png")
            self.generator.save_image_atomic(img, out_path)
            self.assertTrue(os.path.isfile(out_path))
            with open(out_path, "rb") as f:
                self.assertEqual(f.read(4), b"\x89PNG")

            with patch.object(Generator, "_is_reparse_point", side_effect=lambda p: p == os.path.abspath(out_path)):
                with self.assertRaises(ValueError):
                    self.generator.save_image_atomic(img, out_path)

    def test_save_image_atomic_uses_fdopen_and_revalidates_before_replace(self):
        img = Image.new("RGB", (32, 32), color=(10, 20, 30))
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "fdopen_verse.png")
            with patch("generator.os.fdopen", wraps=os.fdopen) as mock_fdopen:
                self.generator.save_image_atomic(img, out_path)
                self.assertTrue(mock_fdopen.called)
            with open(out_path, "rb") as f:
                self.assertEqual(f.read(4), b"\x89PNG")

            # Simulate symlink/junction swap on output_path during PNG encoding
            swapped_path = os.path.join(tmpdir, "swapped.png")
            with patch.object(Generator, "_has_reparse_in_lineage", side_effect=[False, True]):
                with self.assertRaises(ValueError):
                    self.generator.save_image_atomic(img, swapped_path)
            self.assertFalse(os.path.exists(swapped_path))
            self.assertEqual([n for n in os.listdir(tmpdir) if n.startswith(".tmp_img_")], [])

    def test_get_locale_string_blocks_format_attribute_traversal(self):
        rendered = self.generator.get_locale_string(
            "en",
            "alt_text_template",
            description="{verse.__class__}",
            verse="God is love",
            reference="1 John 4:8",
        )
        self.assertIn("{verse.__class__}", rendered)
        self.assertIn("God is love", rendered)

    def test_get_locale_string_single_pass_blocks_token_injection(self):
        rendered = self.generator.get_locale_string(
            "en",
            "alt_text_template",
            description="{verse}",
            verse="Literal {reference} token",
            reference="John 3:16",
        )
        self.assertIn("Literal {reference} token", rendered)
        self.assertEqual(rendered.count("John 3:16"), 1)

    def test_parse_reference_and_get_passage_reject_out_of_bounds_and_invalid_bible_id(self):
        self.assertEqual(GetBibleAPI._parse_reference("Psalms 151:1", lang="en"), (None, None, None, None))
        self.assertEqual(GetBibleAPI._parse_reference("Psalms 0:1", lang="en"), (None, None, None, None))
        self.assertEqual(GetBibleAPI._parse_reference("Psalms 119:201", lang="en"), (None, None, None, None))
        self.assertEqual(GetBibleAPI._parse_reference("Psalms 119:1-201", lang="en"), (None, None, None, None))

        with patch.object(GetBibleAPI, "_fetch_chapter") as mock_fetch:
            self.assertIsNone(GetBibleAPI.get_passage("../evil", "John 3:16", lang="en"))
            self.assertIsNone(GetBibleAPI.get_passage("", "John 3:16", lang="en"))
            mock_fetch.assert_not_called()

    def test_is_valid_raster_image_checks_magic_bytes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_png = os.path.join(tmpdir, "fake.png")
            with open(fake_png, "wb") as f:
                f.write(b"<svg xmlns='http://www.w3.org/2000/svg'/>")
            self.assertFalse(Generator._is_valid_raster_image(fake_png))

            real_png = os.path.join(tmpdir, "real.png")
            Image.new("RGB", (8, 8), color=(0, 0, 0)).save(real_png, "PNG")
            self.assertTrue(Generator._is_valid_raster_image(real_png))

            real_jpg = os.path.join(tmpdir, "real.jpg")
            Image.new("RGB", (8, 8), color=(0, 0, 0)).save(real_jpg, "JPEG")
            self.assertTrue(Generator._is_valid_raster_image(real_jpg))

            # Verify _open_regular_nofollow rejects non-regular mode on open fd (TOCTOU protection)
            with patch("generator.os.fstat", return_value=os.stat_result((0o120777, 0, 0, 1, 0, 0, 10, 0, 0, 0))):
                self.assertFalse(Generator._is_valid_raster_image(real_png))

    def test_load_locales_rejects_unsafe_locale_files(self):
        with patch.object(Generator, "_open_regular_nofollow", side_effect=ValueError("Unsafe or invalid regular file")):
            gen = Generator()
            self.assertEqual(gen.locales, {})

    def test_generate_image_falls_back_when_fstat_exceeds_size_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bg_path = os.path.join(tmpdir, "bg.png")
            Image.new("RGB", (16, 16), color=(200, 100, 50)).save(bg_path, "PNG")
            # Simulate a TOCTOU swap to > 20 MB on fstat after _is_safe_regular_file passed
            oversized_stat = os.stat_result((0o100644, 0, 0, 1, 0, 0, 21 * 1024 * 1024, 0, 0, 0))
            with patch("generator.os.fstat", return_value=oversized_stat):
                img = self.generator.generate_image(
                    "English",
                    "God is love",
                    "1 John 4:8",
                    custom_image_path=bg_path,
                    background_dim=0.0,
                    max_dimension=64,
                )
            self.assertEqual(img.size, (64, 64))
            # Solid fallback color (36, 54, 68) at pixel (0, 0) instead of (200, 100, 50)
            self.assertEqual(img.getpixel((0, 0)), (36, 54, 68))

    def test_generate_audio_uses_fdopen_and_revalidates_before_replace(self):
        class _FakeCommunicate:
            def __init__(self, *_args, **_kwargs):
                pass

            async def stream(self):
                yield {"type": "audio", "data": b"ID3mock"}

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "verse.mp3")
            with patch("generator.edge_tts.Communicate", _FakeCommunicate):
                with patch("generator.os.fdopen", wraps=os.fdopen) as mock_fdopen:
                    result = self.generator.generate_audio(
                        "English",
                        "God is love",
                        "1 John 4:8",
                        custom_output_path=out_path,
                    )
                    self.assertEqual(result, out_path)
                    self.assertTrue(mock_fdopen.called)
            with open(out_path, "rb") as f:
                self.assertEqual(f.read(), b"ID3mock")

            # Simulate symlink/junction swap on output_path during async TTS stream
            swapped_path = os.path.join(tmpdir, "swapped.mp3")
            with patch("generator.edge_tts.Communicate", _FakeCommunicate), patch.object(
                Generator, "_has_reparse_in_lineage", side_effect=[False, True]
            ):
                with self.assertRaises(ValueError):
                    self.generator.generate_audio(
                        "English",
                        "God is love",
                        "1 John 4:8",
                        custom_output_path=swapped_path,
                    )
            self.assertFalse(os.path.exists(swapped_path))
            self.assertEqual([n for n in os.listdir(tmpdir) if n.startswith(".tmp_tts_")], [])

    def test_open_regular_nofollow_blocks_reparse_and_inode_swap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sample = os.path.join(tmpdir, "sample.txt")
            with open(sample, "wb") as f:
                f.write(b"ok")

            # Fallback reparse attribute detection works even when os.path.isjunction is absent (Python <3.12)
            fake_reparse = type("S", (), {"st_file_attributes": 0x400})()
            with patch("generator.os.path.islink", return_value=False), patch(
                "generator.os.path.isjunction", None, create=True
            ), patch("generator.stat.FILE_ATTRIBUTE_REPARSE_POINT", 0x400, create=True), patch(
                "generator.os.lstat", return_value=fake_reparse
            ):
                self.assertTrue(Generator._is_reparse_point(sample))

            # Verify inode mismatch between lstat and fstat is rejected (guards Windows where O_NOFOLLOW is 0)
            lst = os.stat_result((0o100644, 111, 222, 1, 0, 0, 2, 0, 0, 0))
            fst = os.stat_result((0o100644, 999, 222, 1, 0, 0, 2, 0, 0, 0))
            with patch.object(Generator, "_is_safe_regular_file", return_value=True), patch.object(
                Generator, "_is_reparse_point", return_value=False
            ), patch("generator.os.lstat", return_value=lst), patch("generator.os.fstat", return_value=fst):
                with self.assertRaises(ValueError):
                    Generator._open_regular_nofollow(sample, mode="rb")

    def test_has_unsafe_path_syntax_blocks_mixed_slash_device_namespaces(self):
        for payload in [r"/\.\C:\file.png", r"\/?\C:\file.png", "/??/C:/file.png"]:
            self.assertTrue(Generator._has_unsafe_path_syntax(payload), f"Expected rejection for {payload}")

    def test_fetch_chapter_rejects_redirects_and_strips_bidi_control_chars(self):
        class _FakeResponse:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self.headers = {}
                self._payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(f"HTTP {self.status_code}")

            def iter_content(self, chunk_size=8192):
                yield self._payload

        GetBibleAPI._fetch_chapter.cache_clear()
        with patch.object(GetBibleAPI._session, "get", return_value=_FakeResponse(302, b"{}")):
            self.assertIsNone(GetBibleAPI.get_passage("web", "John 3:16", lang="en"))

        GetBibleAPI._fetch_chapter.cache_clear()
        payload = b'{"verses": [{"text": "For God\\u202E so\\u0007 loved\\u2066"}]}'
        with patch.object(GetBibleAPI._session, "get", return_value=_FakeResponse(200, payload)):
            self.assertEqual(GetBibleAPI.get_passage("web", "John 3:1", lang="en"), "For God so loved")


if __name__ == "__main__":
    unittest.main()
