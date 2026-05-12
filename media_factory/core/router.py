from core.validator import FactChecker, CitationChecker


class ModeRouter:
    VALID_MODES = ("trading", "wisdom", "mixed")

    def __init__(self, settings):
        self.settings = settings

    def dispatch(self, mode: str, input_data: dict) -> list[dict]:
        if mode not in self.VALID_MODES:
            raise ValueError(f"非法模式: {mode}，可选: {self.VALID_MODES}")

        if mode == "trading":
            return self._run_trading(input_data)
        elif mode == "wisdom":
            return self._run_wisdom(input_data)
        elif mode == "mixed":
            return self._run_mixed(input_data)

    def _run_trading(self, input_data: dict) -> list[dict]:
        from mode_trading.pipeline import TradingPipeline
        pipeline = TradingPipeline(self.settings)
        return pipeline.run(input_data)

    def _run_wisdom(self, input_data: dict) -> list[dict]:
        from mode_wisdom.pipeline import WisdomPipeline
        pipeline = WisdomPipeline(self.settings)
        return pipeline.run(input_data)

    def _run_mixed(self, input_data: dict) -> list[dict]:
        from mode_mixed.pipeline import MixedPipeline
        pipeline = MixedPipeline(self.settings)
        return pipeline.run(input_data)
