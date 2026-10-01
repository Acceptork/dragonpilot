from openpilot.system.ui.lib.multilang import (
  multilang as base_multilang,
  TRANSLATIONS_DIR,
  tr_noop,
  load_translations,
  PLURAL_SELECTORS,
)


class DpMultilang:
  """Wrapper that syncs with base multilang and adds dragonpilot translations."""

  def __init__(self):
    self._translations: dict[str, str] = {}
    self._plurals: dict[str, list[str]] = {}
    self._loaded_language: str = ""

  @property
  def languages(self):
    """Delegate to base multilang."""
    return base_multilang.languages

  @property
  def language(self):
    """Delegate to base multilang."""
    return base_multilang.language

  def _ensure_loaded(self):
    """Reload dragon translations if base language changed."""
    current_lang = base_multilang.language
    if current_lang != self._loaded_language:
      self._loaded_language = current_lang
      try:
        self._translations, self._plurals = load_translations(
          TRANSLATIONS_DIR.joinpath(f'dragonpilot_{current_lang}.po'))
      except FileNotFoundError:
        self._translations, self._plurals = {}, {}

  def tr(self, text: str) -> str:
    self._ensure_loaded()
    result = self._translations.get(text)
    return result if result and result != text else base_multilang.tr(text)

  def trn(self, singular: str, plural: str, n: int) -> str:
    self._ensure_loaded()
    forms = self._plurals.get(singular, [])
    idx = PLURAL_SELECTORS.get(self.language, lambda count: 0 if count == 1 else 1)(n)
    result = forms[idx] if idx < len(forms) else ""
    return result if result and result not in (singular, plural) else base_multilang.trn(singular, plural, n)


multilang = DpMultilang()

tr, trn = multilang.tr, multilang.trn

__all__ = ['multilang', 'tr', 'trn', 'tr_noop', 'TRANSLATIONS_DIR']
