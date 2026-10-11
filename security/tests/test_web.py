"""XSS, open redirect and upload filtering: the feature works, and the exploit does not."""

from vault.redirect import safe_redirect
from vault.render import render_comment
from vault.upload import allowed_file


def test_render_plain_comment():
    assert render_comment("bob", "nice post") == '<div class="comment"><b>bob</b>: nice post</div>'


def test_exploit_script_in_comment_is_escaped():
    out = render_comment("<img src=x onerror=alert(1)>", "<script>alert('xss')</script>")
    assert "<script>" not in out and "<img" not in out
    assert "&lt;script&gt;" in out and "&lt;img" in out


def test_redirect_to_local_path():
    assert safe_redirect("/dashboard?tab=2") == "/dashboard?tab=2"
    assert safe_redirect("") == "/"


def test_exploit_open_redirect_is_blocked():
    for target in ("https://evil.example/login", "//evil.example/x", "/\\evil.example", "javascript:alert(1)"):
        assert safe_redirect(target) == "/", target


def test_allowed_uploads():
    assert allowed_file("photo.PNG") and allowed_file("scan.pdf") and allowed_file("a.b.jpeg")
    assert not allowed_file("notes.txt") and not allowed_file(".png")


def test_exploit_double_extension_is_rejected():
    assert not allowed_file("invoice.png.exe")
    assert not allowed_file("shell.pdf.php")
