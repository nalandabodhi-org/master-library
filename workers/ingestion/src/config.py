def require_env(env: object, key: str) -> str:
    value = getattr(env, key, None) if not isinstance(env, dict) else env.get(key)
    if not value:
        raise ValueError(f"Missing required env: {key}")
    return value
