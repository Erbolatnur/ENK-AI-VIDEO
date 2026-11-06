import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import video, providers


class VideoTests(unittest.TestCase):
    def setUp(self): self.d = tempfile.mkdtemp()
    def p(self, n): return os.path.join(self.d, n)

    def test_formats(self):
        for a, (w, h) in video.SIZES.items():
            f = self.p(a.replace(":", "x") + ".mp4"); video.make_demo_clip(f, a, 2)
            i = video.probe(f); self.assertEqual((i["width"], i["height"]), (w, h)); self.assertGreater(i["duration"], 1.5)

    def test_image_to_video(self):
        png = self.p("a.png"); video._run(["-f", "lavfi", "-i", "testsrc=s=640x480:d=1", "-frames:v", "1", png])
        f = self.p("i.mp4"); video.make_demo_clip(f, "16:9", 2, image=png); self.assertEqual(video.probe(f)["width"], 1280)

    def test_subtitles_and_concat(self):
        a, b = self.p("a.mp4"), self.p("b.mp4"); video.make_demo_clip(a, "1:1", 2); video.make_demo_clip(b, "1:1", 2, seed=5)
        s = self.p("s.mp4"); video.add_subtitles(a, video.make_srt("Привет. Мир!", 2), s); self.assertIn("subtitle", video.probe(s)["streams"])
        c = self.p("c.mp4"); video.concat([a, b], c); self.assertAlmostEqual(video.probe(c)["duration"], 4, delta=0.3)

    def test_providers(self):
        self.assertTrue(providers.REGISTRY["demo"].available()); self.assertFalse(providers.REGISTRY["fal"].available())
        with self.assertRaises(RuntimeError): providers.REGISTRY["fal"].generate(providers.GenRequest("x", "1:1", 2), "o.mp4", print)


if __name__ == "__main__": unittest.main()
