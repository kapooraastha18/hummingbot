from decimal import Decimal
from typing import Optional

from hummingbot.client.config.config_var import ConfigVar
from hummingbot.client.config.config_validators import (
    validate_bool,
    validate_decimal,
    validate_exchange,
    validate_int,
    validate_market_trading_pair,
)
from hummingbot.client.settings import (
    required_exchanges,
    AllConnectorSettings,
)

def trading_pair_prompt():
    exchange = cm_williams_vix_maker_config_map.get("exchange").value
    example = AllConnectorSettings.get_example_pairs().get(exchange)
    return "Enter the trading pair you would like to trade on %s%s >>> " \
           % (exchange, f" (e.g. {example})" if example else "")

# Strategy specific validation functions
def validate_decimal_0_1(value: str) -> Optional[str]:
    try:
        decimal_value = Decimal(value)
        if not (Decimal("0") <= decimal_value <= Decimal("1")):
            return f"{value} must be between 0 and 1."
    except Exception:
        return f"{value} is not a valid decimal."
    return None

def validate_positive_decimal(value: str) -> Optional[str]:
    try:
        decimal_value = Decimal(value)
        if decimal_value <= Decimal("0"):
            return f"{value} must be positive."
    except Exception:
        return f"{value} is not a valid decimal."
    return None

cm_williams_vix_maker_config_map = {
    "strategy": ConfigVar(
        key="strategy",
        prompt="",
        default="cm_williams_vix_maker"
    ),
    "exchange": ConfigVar(
        key="exchange",
        prompt="Enter your maker spot connector >>> ",
        prompt_on_new=True,
        validator=validate_exchange,
        on_validated=lambda value: required_exchanges.append(value),
    ),
    "trading_pair": ConfigVar(
        key="trading_pair",
        prompt=trading_pair_prompt,
        prompt_on_new=True,
        validator=validate_market_trading_pair,
        on_validated=lambda value: required_exchanges.append(value),
    ),
    "order_amount": ConfigVar(
        key="order_amount",
        prompt="What is the amount of base asset per order? >>> ",
        type_str="decimal",
        validator=validate_positive_decimal,
        prompt_on_new=True,
    ),
    "min_spread": ConfigVar(
        key="min_spread",
        prompt="What is the minimum spread between orders (enter 1 for 1%)? >>> ",
        type_str="decimal",
        default=Decimal("1.0"),
        validator=lambda v: validate_decimal(v, 0, 100, inclusive=False),
        prompt_on_new=True,
    ),
    "max_spread": ConfigVar(
        key="max_spread",
        prompt="What is the maximum spread between orders (enter 1 for 1%)? >>> ",
        type_str="decimal",
        default=Decimal("5.0"),
        validator=lambda v: validate_decimal(v, 0, 100, inclusive=False),
        prompt_on_new=True,
    ),
    "order_refresh_time": ConfigVar(
        key="order_refresh_time",
        prompt="How often do you want to refresh orders (in seconds)? >>> ",
        type_str="float",
        default=30.0,
        validator=lambda v: validate_decimal(v, min_value=0.0, inclusive=False),
        prompt_on_new=True,
    ),
    "filled_order_delay": ConfigVar(
        key="filled_order_delay",
        prompt="How long to wait before placing new orders after fills (in seconds)? >>> ",
        type_str="float",
        default=60.0,
        validator=lambda v: validate_decimal(v, min_value=0.0, inclusive=False),
    ),
    # VIX specific parameters
    "lookback_period": ConfigVar(
        key="lookback_period",
        prompt="Enter lookback period for VIX calculation >>> ",
        type_str="int",
        default=22,
        validator=lambda v: validate_int(v, min_value=1),
        prompt_on_new=True,
    ),
    "bb_length": ConfigVar(
        key="bb_length",
        prompt="Enter Bollinger Band length >>> ",
        type_str="int",
        default=20,
        validator=lambda v: validate_int(v, min_value=1),
        prompt_on_new=True,
    ),
    "bb_std": ConfigVar(
        key="bb_std",
        prompt="Enter Bollinger Band standard deviation multiplier >>> ",
        type_str="float",
        default=2.0,
        validator=lambda v: validate_decimal(v, min_value=0.0, inclusive=False),
        prompt_on_new=True,
    ),
    "high_volatility_multiplier": ConfigVar(
        key="high_volatility_multiplier",
        prompt="Enter spread multiplier for high volatility (e.g. 1.5 for 150% of min_spread) >>> ",
        type_str="decimal",
        default=Decimal("1.5"),
        validator=lambda v: validate_decimal(v, min_value=1.0, inclusive=True),
        prompt_on_new=True,
    ),
    "low_volatility_multiplier": ConfigVar(
        key="low_volatility_multiplier",
        prompt="Enter spread multiplier for low volatility (e.g. 0.5 for 50% of min_spread) >>> ",
        type_str="decimal",
        default=Decimal("0.5"),
        validator=lambda v: validate_decimal(v, min_value=0.0, max_value=1.0, inclusive=True),
        prompt_on_new=True,
    ),
    # Risk management parameters
    "max_position_size": ConfigVar(
        key="max_position_size",
        prompt="Enter maximum position size (in base asset, leave blank for 10x order_amount) >>> ",
        type_str="decimal",
        required_if=lambda: False,
        default=None,
        validator=lambda v: validate_decimal(v, min_value=0.0, inclusive=False) if v is not None else None,
    ),
    "stop_loss_spread": ConfigVar(
        key="stop_loss_spread",
        prompt="At what spread from entry price to place stop loss orders (enter 5 for 5%)? >>> ",
        type_str="decimal",
        default=Decimal("5.0"),
        validator=lambda v: validate_decimal(v, 0, 100, inclusive=False),
        prompt_on_new=True,
    ),
    "take_profit_spread": ConfigVar(
        key="take_profit_spread",
        prompt="At what spread from entry price to place take profit orders (enter 2 for 2%)? >>> ",
        type_str="decimal",
        default=Decimal("2.0"),
        validator=lambda v: validate_decimal(v, 0, 100, inclusive=False),
        prompt_on_new=True,
    ),
    "position_cooling_off": ConfigVar(
        key="position_cooling_off",
        prompt="How long to wait before taking new positions (in seconds)? >>> ",
        type_str="int",
        default=300,
        validator=lambda v: validate_int(v, min_value=0),
        prompt_on_new=True,
    ),
    # Advanced parameters
    "order_optimization_enabled": ConfigVar(
        key="order_optimization_enabled",
        prompt="Do you want to enable best bid ask jumping? (Yes/No) >>> ",
        type_str="bool",
        default=False,
        validator=validate_bool,
    ),
    "logging_options": ConfigVar(
        key="logging_options",
        prompt="Enter logging options (1 for INFO, 2 for DEBUG) >>> ",
        type_str="int",
        default=1,
        validator=lambda v: validate_int(v, 1, 2),
    ),
    "status_report_interval": ConfigVar(
        key="status_report_interval",
        prompt="How often do you want to report status (in seconds) >>> ",
        type_str="float",
        default=900.0,
        validator=lambda v: validate_decimal(v, min_value=0.0, inclusive=False),
    ),
}

     
