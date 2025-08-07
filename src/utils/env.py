import os 
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

def get_env_variable(key: str, default: Optional[str] = None) -> str:
    """
    Utility to get environment variables with optional default.

    Args:
        key (str): The environment variable key.
        default (str, optional): A default value if the key is not found.

    Returns:
        str: The value of the environment variable.

    Raises:
        EnvironmentError: If the variable is not set and no default is provided.
    """
    value  = os.getenv(key, default)
    if value is None:
        raise EnvironmentError(f"Required environment variable '{key}' not set.")
    return value