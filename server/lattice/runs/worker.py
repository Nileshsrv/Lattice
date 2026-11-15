"""Compute worker entry point (DR-4): runs in a separate OS process.

The function below executes inside the worker, so the environment versions it
reports are those of the interpreter that actually computed the result.
"""


def warm() -> None:
    import astropy  # noqa: F401
    import numpy  # noqa: F401
    import scipy  # noqa: F401


def execute_tool(tool_id: str, params: dict, data: dict) -> dict:
    import platform

    import astropy
    import numpy
    import scipy

    from ..physics.constants import CODATA_SOURCE
    from ..tools import registry

    contract, fn = registry.get(tool_id)
    result = fn(params, data)
    environment = {
        "python": platform.python_version(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "astropy": astropy.__version__,
        "constants_source": CODATA_SOURCE,
        "execution_location": "local",
    }
    return {"result": result.model_dump(), "environment": environment}
