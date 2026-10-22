import pytest

from rater.api.ingest import IngestError, check_public_url, normalise_link


def test_drive_and_dropbox_links():
    assert normalise_link("https://drive.google.com/file/d/1AbCdEfGhIjKlMn/view?usp=sharing") == \
        "https://drive.usercontent.google.com/download?id=1AbCdEfGhIjKlMn&export=download&confirm=t"
    assert normalise_link("https://www.dropbox.com/s/x/a.mp4?dl=0").endswith("dl=1")
    assert normalise_link("https://example.com/a.mp4") == "https://example.com/a.mp4"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x/y", "http://localhost/x", "http://10.0.0.1/x", "http://169.254.169.254/latest"])
def test_rejects_unsafe_urls(url):
    with pytest.raises(IngestError):
        check_public_url(url)
