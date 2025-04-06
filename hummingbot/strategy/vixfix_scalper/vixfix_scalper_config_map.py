from decimal import Decimal
from typing import Optional

from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.config.config_validators import (
    validate_exchange,
    validate_market_trading_pair,
    validate_decimal,
    validate_bool
)
from hummingbot.client.settings import AllConnectorSettings

def trading_pair_prompt():
    exchange = vixfix_scalper_config_map.get("connector").value
    example = AllConnectorSettings.get_example_pairs().get(exchange)
    return "Enter the trading pair you would like to trade on %s%s >>> " % (
        exchange,
        f" (e.g. {example})" if example else "",
    )

def validate_trading_pair(value: str) -> Optional[str]:
    exchange = vixfix_scalper_config_map.get("connector").value
    return validate_market_trading_pair(exchange, value)

vixfix_scalper_config_map = {
    "strategy": ConfigVar(
        key="strategy",
        prompt="",
        default="vixfix_scalper"
    ),
    "connector": ConfigVar(
        key="connector",
        prompt="Enter the name of the exchange >>> ",
        prompt_on_new=True,
        validator=validate_exchange,
        default="binance_paper_trade"
    ),
    "market": ConfigVar(
        key="market",
        prompt=trading_pair_prompt,
        prompt_on_new=True,
        validator=validate_trading_pair,
        default="BTC-USDT"
    ),
    "base_order_amount": ConfigVar(
        key="base_order_amount",
        prompt="Enter base order amount (in base asset) >>> ",
        type_str="decimal",
        validator=lambda v: validate_decimal(v, min_value=0),
        default=Decimal("0.001"),
        prompt_on_new=True,
    ),
    "profit_target_pct": ConfigVar(
        key="profit_target_pct",
        prompt="Enter profit target percentage (e.g. 0.003 for 0.3%) >>> ",
        type_str="decimal",
        validator=lambda v: validate_decimal(v, 0, 100, inclusive=True),
        default=Decimal("0.003"),
    ),
    "initial_stop_loss_pct": ConfigVar(
        key="initial_stop_loss_pct",
        prompt="Enter initial stop loss percentage (e.g. 0.005 for 0.5%) >>> ",
        type_str="decimal",
        validator=lambda v: validate_decimal(v, 0, 100, inclusive=True),
        default=Decimal("0.005"),
    ),
}
