"""Responsive token usage dashboard built with PySide6 and QFluentWidgets."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil, floor, log10

from PySide6.QtCharts import QCategoryAxis, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QObject, QPointF, QRunnable, QThreadPool, QTimer, Signal, Slot, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsLineItem, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel, CardWidget, SegmentedWidget, StrongBodyLabel, TitleLabel
from gui.i18n import t


SERIES = (
    ("inputTokens", "dashboard.metrics.inputTokens", QColor("#3b82f6")),
    ("outputTokens", "dashboard.metrics.outputTokens", QColor("#22c55e")),
    ("cachedTokens", "dashboard.metrics.cachedTokens", QColor("#a855f7")),
)

METRIC_CARDS = SERIES + (("cacheHitRate", "dashboard.metrics.cacheHitRate", QColor("#f59e0b")),)


class _UsageLoadSignals(QObject):
    succeeded = Signal(int, str, object)
    failed = Signal(int, str, str)


class _UsageLoadWorker(QRunnable):
    """Load SQLite usage data outside the Qt GUI thread."""

    def __init__(self, request_id: int, period: str):
        super().__init__()
        self.request_id = request_id
        self.period = period
        self.signals = _UsageLoadSignals()

    @Slot()
    def run(self):
        try:
            from app.services.token_usage import query_token_usage_sync

            payload = query_token_usage_sync(self.period)
        except Exception as exc:
            self.signals.failed.emit(self.request_id, self.period, str(exc))
            return
        self.signals.succeeded.emit(self.request_id, self.period, payload)


class _UsageChartView(QChartView):
    """Chart view that reports the mouse across the whole plotting area."""

    plotMouseMoved = Signal(QPointF)
    plotMouseLeft = Signal()

    def __init__(self, chart: QChart, parent=None):
        super().__init__(chart, parent)
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

    def mouseMoveEvent(self, event):
        position = event.position()
        if self.chart().plotArea().contains(position):
            self.plotMouseMoved.emit(position)
        else:
            self.plotMouseLeft.emit()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.plotMouseLeft.emit()
        super().leaveEvent(event)


class _MetricCard(CardWidget):
    def __init__(self, title: str, color: QColor, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(82)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(3)
        self._caption = CaptionLabel(title, self)
        self._caption.setTextColor(color, color)
        self.value = StrongBodyLabel("0", self)
        layout.addWidget(self._caption)
        layout.addWidget(self.value)

    def setTitle(self, title: str):
        """Update the card caption (used on language change)."""
        self._caption.setText(title)


class DashboardInterface(QWidget):
    """Usage dashboard with today, seven-day and thirty-day views."""

    usageRecorded = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardInterface")
        self.setStyleSheet("QWidget#dashboardInterface { background: #ffffff; }")
        self._period = "today"
        self._points: list[dict] = []
        self._data_series: list[QLineSeries] = []
        self._guide_line: QGraphicsLineItem | None = None
        self._y_upper = 1.0
        self._load_request_id = 0
        self._load_workers: dict[int, _UsageLoadWorker] = {}
        self._thread_pool = QThreadPool.globalInstance()
        self._last_database_stamp: tuple | None = None
        self._usage_refresh_pending = False

        # The API and Qt GUI normally share one process, so a successful Token
        # write can refresh the visible dashboard immediately. The timer below
        # is a cheap file-stamp fallback for separate-process development runs.
        from app.services.token_usage import subscribe_token_usage_updates

        self.usageRecorded.connect(self._on_usage_recorded, Qt.QueuedConnection)
        self._unsubscribe_usage_updates = subscribe_token_usage_updates(self._emit_usage_recorded)
        self.destroyed.connect(self._unsubscribe_usage_listener)

        self._database_poll_timer = QTimer(self)
        self._database_poll_timer.setInterval(2000)
        self._database_poll_timer.timeout.connect(self._poll_database_change)
        self._database_poll_timer.start()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 28)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        self._title_label = TitleLabel(t("dashboard.title"), self)
        title_col.addWidget(self._title_label)
        self._subtitle_label = CaptionLabel(t("dashboard.subtitle"), self)
        self._subtitle_label.setTextColor(QColor("#777777"), QColor("#aaaaaa"))
        title_col.addWidget(self._subtitle_label)
        header.addLayout(title_col)
        header.addStretch(1)

        self._period_selector = SegmentedWidget(self)
        for route_key, text in (("today", t("dashboard.period.today")), ("7d", t("dashboard.period.7d"))):
            self._period_selector.addItem(routeKey=route_key, text=text)
        self._period_selector.setCurrentItem("today")
        self._period_selector.currentItemChanged.connect(self._set_period)
        header.addWidget(self._period_selector, alignment=Qt.AlignVCenter)
        root.addLayout(header)

        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self._metric_cards: dict[str, _MetricCard] = {}
        self._metric_title_keys: dict[str, str] = {}
        for key, title_key, color in METRIC_CARDS:
            card = _MetricCard(t(title_key), color, self)
            self._metric_cards[key] = card
            self._metric_title_keys[key] = title_key
            metrics.addWidget(card, 1)
        root.addLayout(metrics)

        chart_card = CardWidget(self)
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(14, 14, 14, 10)
        chart_layout.setSpacing(8)
        chart_header = QHBoxLayout()
        self._chart_title_label = StrongBodyLabel(t("dashboard.chart.trend"), chart_card)
        chart_header.addWidget(self._chart_title_label)
        chart_header.addStretch(1)
        self._status = BodyLabel(t("dashboard.status.loading"), chart_card)
        self._status.setStyleSheet("color: #888888;")
        chart_header.addWidget(self._status)
        chart_layout.addLayout(chart_header)

        self._chart = QChart()
        self._chart.setBackgroundVisible(False)
        self._chart.setPlotAreaBackgroundVisible(False)
        self._chart.legend().setAlignment(Qt.AlignBottom)
        self._guide_line = QGraphicsLineItem(self._chart)
        self._guide_line.setPen(QPen(QColor("#a3a3a3"), 1.1, Qt.DashLine))
        self._guide_line.setZValue(10)
        self._guide_line.setAcceptedMouseButtons(Qt.NoButton)
        self._guide_line.hide()
        self._chart_view = _UsageChartView(self._chart, chart_card)
        self._chart_view.setRenderHint(QPainter.Antialiasing)
        self._chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._chart_view.setMinimumHeight(280)
        self._chart_view.setStyleSheet("background: #ffffff; border: none; border-radius: 8px;")
        self._chart_view.plotMouseMoved.connect(self._show_plot_hover)
        self._chart_view.plotMouseLeft.connect(self._hide_hover)
        chart_layout.addWidget(self._chart_view, 1)

        self._detail_label = QLabel(self._chart_view)
        self._detail_label.setTextFormat(Qt.RichText)
        self._detail_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._detail_label.setStyleSheet(
            "QLabel { background: rgba(255, 255, 255, 245); color: #202020; "
            "border: 1px solid #dedede; border-radius: 8px; padding: 9px 11px; }"
        )
        self._detail_label.hide()
        root.addWidget(chart_card, 1)

        from gui.i18n import subscribe_locale_changed

        subscribe_locale_changed(self._retranslate)

    def _retranslate(self, _locale: str = ""):
        """Update all translatable labels on this page after a language change."""
        self._title_label.setText(t("dashboard.title"))
        self._subtitle_label.setText(t("dashboard.subtitle"))
        self._chart_title_label.setText(t("dashboard.chart.trend"))
        for route_key, text in (("today", t("dashboard.period.today")), ("7d", t("dashboard.period.7d"))):
            item = self._period_selector.widget(route_key)
            if item is not None:
                item.setText(text)
        # METRIC_CARDS now stores i18n keys; resolve t() for each card.
        for key, card in self._metric_cards.items():
            title_key = self._metric_title_keys.get(key)
            if title_key is not None:
                card.setTitle(t(title_key))
        for series, (_, title_key, _) in zip(self._data_series, SERIES):
            series.setName(t(title_key))
        self.refresh()

    def _set_period(self, period: str):
        if self._period == period:
            return
        self._period = period
        self.refresh()

    def _emit_usage_recorded(self):
        """May be called by the API thread; Qt queues the actual UI update."""
        self.usageRecorded.emit()

    @Slot()
    def _on_usage_recorded(self):
        self._last_database_stamp = self._database_stamp()
        if self.isVisible():
            self.refresh()
        else:
            self._usage_refresh_pending = True

    @Slot()
    def _poll_database_change(self):
        if not self.isVisible():
            return
        current_stamp = self._database_stamp()
        if self._last_database_stamp is None:
            self._last_database_stamp = current_stamp
            return
        if current_stamp != self._last_database_stamp:
            self._last_database_stamp = current_stamp
            self.refresh()

    @staticmethod
    def _database_stamp() -> tuple:
        try:
            from app.core.config import get_data_dir

            db_path = get_data_dir() / "wence_ai.db"
            candidates = (db_path, db_path.with_name(f"{db_path.name}-wal"))
            return tuple(
                (path.exists(), path.stat().st_mtime_ns, path.stat().st_size) if path.exists() else (False, 0, 0)
                for path in candidates
            )
        except OSError:
            return ()

    @Slot()
    def _unsubscribe_usage_listener(self, *_args):
        unsubscribe = getattr(self, "_unsubscribe_usage_updates", None)
        if unsubscribe is not None:
            unsubscribe()
            self._unsubscribe_usage_updates = None

    @staticmethod
    def _adaptive_y_axis(max_value: int) -> tuple[float, int]:
        """Return a pleasant data-dependent upper bound and tick count."""
        if max_value <= 0:
            return 1.0, 2
        target = max_value * 1.1
        rough_step = target / 5
        magnitude = 10 ** floor(log10(rough_step))
        fraction = rough_step / magnitude
        if fraction <= 1:
            nice_fraction = 1
        elif fraction <= 2:
            nice_fraction = 2
        elif fraction <= 5:
            nice_fraction = 5
        else:
            nice_fraction = 10
        step = nice_fraction * magnitude
        upper = ceil(target / step) * step
        return float(upper), int(round(upper / step)) + 1

    def refresh(self):
        self._last_database_stamp = self._database_stamp()
        self._usage_refresh_pending = False
        self._load_request_id += 1
        request_id = self._load_request_id
        period = self._period
        self._status.setText("正在加载…")
        self._status.setStyleSheet("color: #888888;")
        self._status.setToolTip("")

        worker = _UsageLoadWorker(request_id, period)
        worker.signals.succeeded.connect(self._on_load_succeeded)
        worker.signals.failed.connect(self._on_load_failed)
        self._load_workers[request_id] = worker
        self._thread_pool.start(worker)

    @Slot(int, str, object)
    def _on_load_succeeded(self, request_id: int, period: str, payload: object):
        self._load_workers.pop(request_id, None)
        if request_id != self._load_request_id or period != self._period:
            return
        if not isinstance(payload, dict):
            self._on_load_failed(request_id, period, t("dashboard.status.invalid"))
            return
        self._render(payload)
        has_usage = any(int(value or 0) for value in payload.get("totals", {}).values())
        self._status.setText(t("dashboard.status.hover") if has_usage else t("dashboard.status.empty"))

    @Slot(int, str, str)
    def _on_load_failed(self, request_id: int, period: str, error: str):
        self._load_workers.pop(request_id, None)
        if request_id != self._load_request_id or period != self._period:
            return
        self._render(self._zero_payload())
        self._status.setText(t("dashboard.status.failed"))
        self._status.setStyleSheet("color: #dc2626;")
        self._status.setToolTip(error)

    def _zero_payload(self) -> dict:
        now = datetime.now()
        if self._period == "today":
            timestamps = [
                now.replace(hour=hour, minute=0, second=0, microsecond=0).isoformat() for hour in range(now.hour + 1)
            ]
        else:
            first_day = now.date() - timedelta(days=6)
            timestamps = [(first_day + timedelta(days=offset)).isoformat() for offset in range(7)]
        points = [
            {"timestamp": timestamp, "inputTokens": 0, "outputTokens": 0, "cachedTokens": 0} for timestamp in timestamps
        ]
        return {
            "range": self._period,
            "points": points,
            "totals": {"inputTokens": 0, "outputTokens": 0, "cachedTokens": 0},
        }

    def _render(self, payload: dict):
        totals = payload.get("totals") if isinstance(payload.get("totals"), dict) else {}
        for key, card in self._metric_cards.items():
            if key == "cacheHitRate":
                input_tokens = max(0, int(totals.get("inputTokens", 0) or 0))
                cached_tokens = max(0, int(totals.get("cachedTokens", 0) or 0))
                total_prompt_tokens = input_tokens + cached_tokens
                hit_rate = min(100.0, cached_tokens / total_prompt_tokens * 100) if total_prompt_tokens else 0.0
                card.value.setText(f"{hit_rate:.1f}%")
            else:
                card.value.setText(f"{int(totals.get(key, 0) or 0):,}")

        raw_points = payload.get("points")
        self._points = raw_points if isinstance(raw_points, list) else []
        self._detail_label.hide()
        self._data_series.clear()
        if self._guide_line is not None:
            self._guide_line.hide()
        self._chart.removeAllSeries()
        for axis in list(self._chart.axes()):
            self._chart.removeAxis(axis)
        if not self._points:
            self._chart.setTitle(t("dashboard.chart.empty"))
            return
        self._chart.setTitle("")

        max_y = max((int(point.get(key, 0) or 0) for point in self._points for key, _, _ in SERIES), default=0)
        axis_x = QCategoryAxis()
        axis_x.setStartValue(-0.5)
        for index, point in enumerate(self._points):
            parsed = datetime.fromisoformat(str(point["timestamp"]))
            label = parsed.strftime("%H:00" if self._period == "today" else "%m/%d")
            axis_x.append(label, index + 0.5)
        axis_x.setRange(-0.5, len(self._points) - 0.5)
        axis_x.setLabelsPosition(QCategoryAxis.AxisLabelsPositionCenter)
        axis_x.setLabelsAngle(-45 if self._period == "today" and len(self._points) > 12 else 0)
        axis_x.setGridLineVisible(False)
        axis_x.setMinorGridLineVisible(False)
        axis_y = QValueAxis()
        y_upper, y_tick_count = self._adaptive_y_axis(max_y / 1000)
        self._y_upper = y_upper
        axis_y.setRange(0, self._y_upper)
        if self._y_upper < 0.1:
            axis_y.setLabelFormat("%.3fk")
        elif self._y_upper < 1:
            axis_y.setLabelFormat("%.2fk")
        elif self._y_upper < 10:
            axis_y.setLabelFormat("%.1fk")
        else:
            axis_y.setLabelFormat("%.0fk")
        axis_y.setTickCount(y_tick_count)
        axis_y.setTitleText("Token")
        axis_y.setGridLineVisible(False)
        axis_y.setMinorGridLineVisible(False)
        self._chart.addAxis(axis_x, Qt.AlignBottom)
        self._chart.addAxis(axis_y, Qt.AlignLeft)

        for key, title_key, color in SERIES:
            series = QLineSeries()
            for index, point in enumerate(self._points):
                series.append(index, max(0.0, int(point.get(key, 0) or 0) / 1000))
            series.setPointsVisible(len(self._points) == 1)
            series.setName(t(title_key))
            series.setPen(QPen(color, 2.4))
            self._chart.addSeries(series)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
            self._data_series.append(series)

    def _hide_hover(self):
        if self._guide_line is not None:
            self._guide_line.hide()
        self._detail_label.hide()

    def _show_plot_hover(self, position: QPointF):
        if not self._points:
            self._hide_hover()
            return
        plot_area = self._chart.plotArea()
        if plot_area.width() <= 0 or not plot_area.contains(position):
            self._hide_hover()
            return
        relative_x = (position.x() - plot_area.left()) / plot_area.width()
        chart_x = -0.5 + relative_x * len(self._points)
        index = max(0, min(len(self._points) - 1, round(chart_x)))
        self._show_node_detail(index)

    def _show_node_detail(self, index: int):
        item = self._points[index]
        raw_time = str(item.get("timestamp", ""))
        try:
            parsed = datetime.fromisoformat(raw_time)
            label = parsed.strftime("%Y/%m/%d %H:00" if self._period == "today" else "%Y/%m/%d")
        except ValueError:
            label = raw_time
        text = (
            f"<b>{label}</b><br>"
            f"<span style='color:#3b82f6'>● {t('dashboard.tooltip.input')}</span>{int(item.get('inputTokens', 0)):,}<br>"
            f"<span style='color:#22c55e'>● {t('dashboard.tooltip.output')}</span>{int(item.get('outputTokens', 0)):,}<br>"
            f"<span style='color:#a855f7'>● {t('dashboard.tooltip.cached')}</span>{int(item.get('cachedTokens', 0)):,}"
        )
        self._detail_label.setText(text)
        self._detail_label.adjustSize()
        reference = self._data_series[0] if self._data_series else None
        chart_pos = self._chart.mapToPosition(QPointF(index, 0), reference)
        plot_area = self._chart.plotArea()
        if self._guide_line is not None:
            self._guide_line.setLine(chart_pos.x(), plot_area.top(), chart_pos.x(), plot_area.bottom())
            self._guide_line.show()
        gap = 12
        if chart_pos.x() + gap + self._detail_label.width() <= plot_area.right():
            label_x = chart_pos.x() + gap
        else:
            label_x = chart_pos.x() - self._detail_label.width() - gap
        label_x = max(plot_area.left(), min(label_x, plot_area.right() - self._detail_label.width()))
        label_y = max(plot_area.top() + 10, 0)
        self._detail_label.move(round(label_x), round(label_y))
        self._detail_label.show()
        self._detail_label.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
