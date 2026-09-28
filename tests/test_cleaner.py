"""
tests/test_cleaner.py

Basic tests for preprocessing/cleaner.py
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from preprocessing.cleaner import clean_text


def test_removes_url():
    assert "http" not in clean_text("Check this out https://example.com")


def test_lowercases():
    assert clean_text("HEAVY RAIN") == "heavy rain"


def test_collapses_punctuation():
    assert "!!!" not in clean_text("Flooding!!! everywhere")


if __name__ == "__main__":
    test_removes_url()
    test_lowercases()
    test_collapses_punctuation()
    print("All cleaner tests passed.")
