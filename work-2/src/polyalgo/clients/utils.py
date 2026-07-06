def clean_params(params: dict) -> dict:
    return {k: v for k, v in params.items() if v is not None}

