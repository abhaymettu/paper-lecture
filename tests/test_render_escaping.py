"""Escaping regressions. Run: python tests/test_render_escaping.py"""
import importlib.util
import json
import os

spec = importlib.util.spec_from_file_location(
    "render", os.path.join(os.path.dirname(__file__), "..", "bin", "render.py"))
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)

HOSTILE = [
    "plain text",
    "</script><script>alert(document.domain)</script>",
    "a < b and c > d",
    'a quote " and an apostrophe \'',
    "  line separator  ",
    "rho = -0.83, n = 535",
]


def test_js_json_is_lossless_and_cannot_close_the_script_tag():
    for s in HOSTILE:
        blob = render.js_json({"narration": s})
        assert json.loads(blob)["narration"] == s, f"lost content: {s!r}"
        assert "</script" not in blob.lower(), f"can close script tag: {s!r}"


def test_esc_escapes_quotes_because_output_lands_in_attributes():
    assert render.esc('x" onmouseover="alert(1)') == "x&quot; onmouseover=&quot;alert(1)"
    assert render.esc("<b>&</b>") == "&lt;b&gt;&amp;&lt;/b&gt;"


if __name__ == "__main__":
    test_js_json_is_lossless_and_cannot_close_the_script_tag()
    test_esc_escapes_quotes_because_output_lands_in_attributes()
    print("ok")
