"""Caption detection must not fire on sentences that merely mention a figure.

Run: python tests/test_caption_match.py
The real strings below are from papers 01, 02 and 19 in the source corpus.
"""
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "extract", os.path.join(os.path.dirname(__file__), "..", "bin", "extract.py"))
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)

REAL_CAPTIONS = [
    ("Fig. 1. Model simulations illustrating generic indicators", ("fig", "1")),
    ("Fig. 1. Frequencies of the 30 most common depression symptom", ("fig", "1")),
    ("Table 1 Number of symptoms that appear across combinations", ("table", "1")),
    ("TABLE 4 EMA descriptives.", ("table", "4")),
    ("FIGURE 3 Control limits for all seven personalization settings", ("figure", "3")),
    ("Figure 2: Something with a colon", ("figure", "2")),
    ("Table 1", ("table", "1")),                       # bare label, caption body elsewhere
]

BODY_REFERENCES = [
    "Table 1 lists in how many scales each of the symptoms are listed",
    "Table 2 summarizes to what degree the symptoms in each scale",
    "Fig. 1 illustrates the frequencies of the 30 most common",
    "Figure 3 shows the distribution of warning signals",
    "Table 5 presents descriptive statistics for the sample",
]


def test_real_captions_are_detected():
    for text, expected in REAL_CAPTIONS:
        assert extract.caption_match(text) == expected, f"missed caption: {text!r}"


def test_body_references_are_rejected():
    for text in BODY_REFERENCES:
        assert extract.caption_match(text) is None, f"false positive: {text!r}"


def test_non_captions_are_rejected():
    for text in ["Introduction", "We found that", "", "Figure of merit is high"]:
        assert extract.caption_match(text) is None, text


if __name__ == "__main__":
    test_real_captions_are_detected()
    test_body_references_are_rejected()
    test_non_captions_are_rejected()
    print("ok")
