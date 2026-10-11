from mend.site import render


def test_site_renders_from_run_files():
    page = render()
    assert "gents that fix themselves, and prove it." in page and 'id="rounds"' in page and 'id="evidence"' in page


def test_hardware_page_numbers_come_from_run_files():
    from mend import beyond
    page = beyond.render()
    assert "Same 9/9, at 58% fewer tokens." in page and "Same 8/8, at 64% fewer tokens." in page
    assert page.count('class="wave"') == 3 and page.count("docs/img/schematics/") == 7
