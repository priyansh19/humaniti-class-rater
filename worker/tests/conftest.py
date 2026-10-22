import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIX = os.path.join(os.path.dirname(__file__), "fixtures")
NAMES = ["Meera", "Arjun", "Sharma", "Kavya"]


@pytest.fixture
def vtt_text():
    return open(os.path.join(FIX, "synthetic_class.vtt"), encoding="utf-8").read()


needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


@pytest.fixture(scope="session")
def synthetic_mp4(tmp_path_factory):
    """30 s synthetic test pattern + tone. Never a real recording."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    p = tmp_path_factory.mktemp("media") / "synthetic.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=5:duration=30",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=30", "-shortest", "-pix_fmt", "yuv420p", str(p)],
                   check=True)
    return str(p)
