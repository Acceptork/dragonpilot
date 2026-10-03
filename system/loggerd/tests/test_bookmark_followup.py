"""Continuation segments count toward retention without consuming bookmark slots."""

from openpilot.system.loggerd import deleter


def test_followup_preserves_next_segment_without_consuming_bookmark_slots(monkeypatch):
  route = "2026-10-03--08-00-00--abc"
  dirs = [f"{route}--{i}" for i in range(22)]
  primary = {f"{route}--{i}" for i in (0, 4, 8, 12, 16, 20)}
  followup = {f"{route}--{i}" for i in (1, 5, 9, 13, 17, 21)}
  monkeypatch.setattr(deleter, "has_preserve_xattr", lambda d: d in primary)
  monkeypatch.setattr(deleter, "has_followup_xattr", lambda d: d in followup)
  retained = deleter.get_preserved_segments(dirs)
  assert f"{route}--0" not in retained
  for segment in (4, 5, 8, 9, 12, 13, 16, 17, 20, 21):
    assert f"{route}--{segment}" in retained
