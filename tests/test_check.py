"""The linter must actually catch the things that otherwise fail silently."""
import importlib.util, json, os, tempfile

spec = importlib.util.spec_from_file_location(
    "check", os.path.join(os.path.dirname(__file__), "..", "bin", "check.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def lint(lesson):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "lesson.json")
    json.dump(lesson, open(p, "w"))
    return check.check(p)


def test_dangling_focus_target_is_an_error():
    probs, _ = lint({"paper": {"short": "x"}, "slides": [
        {"title": "t", "points": ["a"], "narration": "One. Two.",
         "focus": [None, "point:9"]}]})
    assert any("point:9" in p for p in probs), probs


def test_focus_longer_than_narration_is_an_error():
    probs, _ = lint({"paper": {"short": "x"}, "slides": [
        {"title": "t", "points": ["a"], "narration": "Only one sentence.",
         "focus": [None, "point:0", "point:0"]}]})
    assert any("never fire" in p for p in probs), probs


def test_missing_figure_is_an_error():
    probs, _ = lint({"paper": {"short": "x"}, "slides": [
        {"title": "t", "figure": "nope.png", "narration": "A."}]})
    assert any("not found" in p for p in probs), probs


def test_a_good_lesson_is_clean():
    probs, _ = lint({"paper": {"short": "x"}, "slides": [
        {"title": "t", "points": ["a", "b"], "narration": "One. Two.",
         "focus": [None, "point:1"],
         "check": {"q": "q", "a": "a", "why": "w"}}]})
    assert probs == [], probs


if __name__ == "__main__":
    for fn in [v for k, v in sorted(globals().items()) if k.startswith("test_")]:
        fn()
    print("ok")
