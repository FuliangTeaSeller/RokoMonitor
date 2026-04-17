"""支持拼音首字母匹配的 QCompleter"""

from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtWidgets import QCompleter


class PinyinFilterProxyModel(QSortFilterProxyModel):
    """支持拼音首字母过滤的代理模型"""

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        from src.utils.pinyin_service import PinyinService

        index = self.sourceModel().index(source_row, 0, source_parent)
        text = self.sourceModel().data(index)

        if not text:
            return False

        filter_text = self.filterRegularExpression().pattern()
        if not filter_text:
            return True

        return PinyinService.match(text, filter_text)


class PinyinCompleter(QCompleter):
    """支持拼音首字母匹配的 Completer"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proxy_model = PinyinFilterProxyModel(self)
        self._proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        super().setModel(self._proxy_model)

    def setSourceModel(self, model):
        self._proxy_model.setSourceModel(model)
