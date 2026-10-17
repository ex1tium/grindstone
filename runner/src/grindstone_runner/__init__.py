"""Check-station job executor.

Runs inside the project's declared toolchain image with no credentials and
talks to the control plane only through job directories on the `runs`
volume (Components tab, "Runner job format"). Standard library only.
"""

__version__ = "0.0.0"
