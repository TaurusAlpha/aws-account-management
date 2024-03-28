from core.utils.sso_admin_utils import get_instance_arns

import logging
import os
import time
from typing import Any, Callable, Mapping


INSTANCE_ARNS = get_instance_arns()

logger = logging.getLogger()
logging.basicConfig(format="%(asctime)s %(message)s")
logger.setLevel(logging.INFO if os.getenv("logger_level") else logging.DEBUG)


def block_until_complete(
    task: Callable[..., Any],
    args: list[Any],
    kwargs: Mapping[str, Any],
    condition: Callable[..., bool],
    sleep_time: float = 5,
    timeout: float = 30,
) -> dict[str, Any]:
    """Executes a task repeatedly until a condition is met or a timeout occurs.

    Args:
        task (Callable): The callable task to execute.
        args (list): A list of arguments to pass to the task.
        kwargs (Mapping[str, Any]): A dictionary of keyword arguments to pass to the task.
        condition (Callable): A callable that takes the task's response and returns a bool.
        sleep_time (float, optional): Time to wait between retries (in seconds). Defaults to 5.
        timeout (float, optional): Maximum time to wait for the condition to be met (in seconds). Defaults to 30.

    Raises:
        TimeoutError: If the operation times out.
    """
    start_time = time.time()

    response = task(*args, **kwargs)
    logger.info(f"Initial request: {response}")

    # TODO: Because AWS API is used, can we proceed after sleep_time reached?
    while condition(response):
        if time.time() - start_time > timeout:
            raise TimeoutError("Operation timed out.")
        time.sleep(sleep_time)
        response = task(*args, **kwargs)
        logger.info(f"Running request: {response}")

    return response
