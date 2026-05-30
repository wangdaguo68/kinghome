from pathlib import Path

from app.backtest.fees import BrokerFeeModel, load_broker_fee_model


def test_loads_king_statement_fee_model() -> None:
    model = load_broker_fee_model(Path(__file__).resolve().parents[2] / "data" / "king.xls")

    assert model.sample_count == 416
    assert model.min_commission == 5
    assert 0.00049 < model.stamp_tax_rate < 0.00051
    assert 0.000009 < model.transfer_fee_rate < 0.000011
    assert model.commission_rate == 0
    assert model.commission_rate_upper_bound > 0


def test_estimates_buy_sell_fee_with_min_commission_stamp_and_transfer() -> None:
    model = BrokerFeeModel("test", 1, 5, 0, 0.0002, 0.0005, 0.00001)

    sh_fee = model.estimate_fee("600000.SH", 10000, 11000)
    sz_fee = model.estimate_fee("000001.SZ", 10000, 11000)

    assert sh_fee == 15.71
    assert sz_fee == 15.5
