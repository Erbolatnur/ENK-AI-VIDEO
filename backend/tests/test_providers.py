import io, os, sys, tempfile, unittest
from unittest import mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import providers
from app.providers import GenRequest

SUB = {"request_id": "1", "status_url": "https://queue.fal.run/m/requests/1/status", "response_url": "https://queue.fal.run/m/requests/1"}


class FalTests(unittest.TestCase):
    def setUp(self):
        self.out = os.path.join(tempfile.mkdtemp(), "o.mp4")
        self.env = mock.patch.dict(os.environ, {"FAL_KEY": "k", "FAL_MODEL_ID": "owner/app"})
        self.env.start(); self.addCleanup(self.env.stop)

    def test_happy_path(self):
        calls = []
        def fake(method, url, key, body=None, timeout=60):
            calls.append((method, url, body))
            return [SUB, {"status": "COMPLETED"}, {"video": {"url": "https://v3.fal.media/f.mp4"}}][len(calls) - 1]
        with mock.patch.object(providers, "_http", fake), \
             mock.patch.object(providers.urllib.request, "urlopen", return_value=io.BytesIO(b"MP4DATA")):
            providers.REGISTRY["fal"].generate(GenRequest("кот", "9:16", 5), self.out, lambda p: None)
        self.assertEqual(calls[0][:2], ("POST", "https://queue.fal.run/owner/app"))
        self.assertEqual(calls[0][2], {"prompt": "кот", "aspect_ratio": "9:16", "duration": 5})
        self.assertEqual(open(self.out, "rb").read(), b"MP4DATA")

    def test_guards(self):
        p = providers.REGISTRY["fal"]
        with self.assertRaises(RuntimeError): p.generate(GenRequest("x", "1:1", 5, image_path="a.png"), self.out, print)
        with self.assertRaises(RuntimeError): p.generate(GenRequest("x", "1:1", 15), self.out, print)
        with mock.patch.object(providers, "_http", return_value={**SUB, "status_url": "https://evil.example/s"}):
            with self.assertRaises(RuntimeError): p.generate(GenRequest("x", "1:1", 5), self.out, print)

    def test_availability(self):
        self.assertTrue(providers.REGISTRY["fal"].available())
        with mock.patch.dict(os.environ, {"FAL_KEY": ""}): self.assertFalse(providers.REGISTRY["fal"].available())


if __name__ == "__main__": unittest.main()
