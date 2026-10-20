"""Bluestar Sniper - ICT signal engine (read-only scanner).

Layering (strict, no cycles):
    config     <- no internal imports
    clock      <- no internal imports
    indicators <- config
    data       <- config, clock
    signals    <- config, clock, indicators
    scoring    <- config, indicators, signals
    ui         <- config, clock, scoring, signals
    app        <- everything (thin entry point)
"""

__version__ = "17.0.0"
