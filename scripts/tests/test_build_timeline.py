"""Tests for build_timeline utility functions."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from build_timeline import get_decade, group_papers_by_topic_decade


def test_get_decade():
    assert get_decade(1975) == 1970
    assert get_decade(1980) == 1980
    assert get_decade(1989) == 1980
    assert get_decade(2023) == 2020


def test_group_papers_single_match():
    papers = [
        {"id": "W1", "year": 1982, "title": "casing treatment study",
         "topics_matched": ["机匣处理"], "tags": []},
    ]
    topics = [{"label": "机匣处理"}, {"label": "叶尖间隙"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["机匣处理"][1980] == ["W1"]
    assert "叶尖间隙" not in result or 1980 not in result.get("叶尖间隙", {})


def test_group_papers_uses_topics_matched_for_historical():
    # Historical paper (has topics_matched, no tags)
    papers = [
        {"id": "W2", "year": 1990, "title": "inlet distortion fan",
         "topics_matched": ["进气畸变"], "tags": []},
    ]
    topics = [{"label": "进气畸变"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["进气畸变"][1990] == ["W2"]


def test_group_papers_uses_tags_for_current():
    # Current paper (has tags, no topics_matched)
    papers = [
        {"id": "W3", "year": 2021, "title": "compressor tip clearance",
         "topics_matched": [], "tags": ["叶尖间隙"]},
    ]
    topics = [{"label": "叶尖间隙"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["叶尖间隙"][2020] == ["W3"]


def test_group_papers_deduplicates():
    papers = [
        {"id": "W4", "year": 1985, "topics_matched": ["机匣处理"], "tags": ["机匣处理"]},
    ]
    topics = [{"label": "机匣处理"}]
    result = group_papers_by_topic_decade(papers, topics)
    assert result["机匣处理"][1980].count("W4") == 1
