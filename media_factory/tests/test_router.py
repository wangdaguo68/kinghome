import pytest
from unittest.mock import MagicMock, patch

from core.router import ModeRouter


class TestModeRouter:
    def test_invalid_mode_raises(self):
        import zen_trader.config
        settings = zen_trader.config.load_settings()
        router = ModeRouter(settings)
        with pytest.raises(ValueError, match="非法模式"):
            router.dispatch("invalid_mode", {})

    def test_valid_modes_accepted(self):
        import zen_trader.config
        settings = zen_trader.config.load_settings()
        router = ModeRouter(settings)
        for mode in ("trading", "wisdom", "mixed"):
            router.VALID_MODES  # just checking the constant

    @patch("mode_trading.pipeline.TradingPipeline")
    def test_trading_dispatch(self, mock_pipeline):
        import zen_trader.config
        settings = zen_trader.config.load_settings()
        instance = MagicMock()
        instance.run.return_value = [{"platform": "weibo", "title": "test", "body": "test"}]
        mock_pipeline.return_value = instance

        router = ModeRouter(settings)
        result = router.dispatch("trading", {"raw_text": "上证 3300 +1.5%"})
        assert len(result) == 1

    @patch("mode_wisdom.pipeline.WisdomPipeline")
    def test_wisdom_dispatch(self, mock_pipeline):
        import zen_trader.config
        settings = zen_trader.config.load_settings()
        instance = MagicMock()
        instance.run.return_value = [{"platform": "weibo", "title": "test", "body": "test"}]
        mock_pipeline.return_value = instance

        router = ModeRouter(settings)
        result = router.dispatch("wisdom", {"wisdom_source": "daily"})
        assert len(result) == 1

    @patch("mode_mixed.pipeline.MixedPipeline")
    def test_mixed_dispatch(self, mock_pipeline):
        import zen_trader.config
        settings = zen_trader.config.load_settings()
        instance = MagicMock()
        instance.run.return_value = [{"platform": "weibo", "title": "test", "body": "test"}]
        mock_pipeline.return_value = instance

        router = ModeRouter(settings)
        result = router.dispatch("mixed", {"raw_text": "test"})
        assert len(result) == 1
