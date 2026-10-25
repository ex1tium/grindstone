"""Crash scenarios, one module per module that owns external steps.

Each module declares its steps' scenarios with `crash_scenario`; the harness
imports every module here, and the matrix runs each scenario at every kill
point of its step.
"""
