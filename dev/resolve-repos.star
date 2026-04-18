# =============================================================================
# Repo Path Resolver
# =============================================================================
# Resolves sibling repository paths with a 3-tier fallback:
#   1. repos.env file (if present, gitignored for local overrides)
#   2. Tilt config / environment variables
#   3. Default relative paths from the calling Tiltfile
#
# Usage:
#   load("resolve-repos.star", "resolve_repo")
#   BACKEND = resolve_repo("stoat-backend")
#   DSS = resolve_repo("discord-stoat-sync")
# =============================================================================

# Default directory names for each repo (matches GitLab repo names)
_REPO_DEFAULTS = {
    "stoat-backend": "stoat-backend",
    "stoat-frontend": "stoat-frontend",
    "stoat-flutter": "stoat-flutter",
    "stoat-sdk-dart": "stoat-sdk-dart",
    "discord-stoat-sync": "discord-stoat-sync",
    "knowledge-browser": "knowledge-browser",
    "chat": "chat",
    "stoat-community": "stoat-community",
}

# Environment variable names for each repo (uppercase, underscored)
_REPO_ENV_VARS = {
    "stoat-backend": "STOAT_BACKEND",
    "stoat-frontend": "STOAT_FRONTEND",
    "stoat-flutter": "STOAT_FLUTTER",
    "stoat-sdk-dart": "STOAT_SDK_DART",
    "discord-stoat-sync": "DSS_PATH",
    "knowledge-browser": "KB_PATH",
    "chat": "CHAT_PATH",
    "stoat-community": "COMMUNITY_PATH",
}

# Parse repos.env eagerly at load time (Starlark freezes module state after load)
_repos_env_cache = {}
_module_dir = os.path.dirname(__file__)
_env_path = os.path.join(_module_dir, "repos.env")
if os.path.exists(_env_path):
    _content = str(read_file(_env_path))
    for _line in _content.splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _value = _line.partition("=")
            _key = _key.strip()
            _value = _value.strip().strip('"').strip("'")
            if _value:
                _repos_env_cache[_key] = _value

def resolve_repo(name, base_dir=None):
    """Resolve a sibling repo path.

    Args:
        name: Repo name (e.g. "stoat-backend", "discord-stoat-sync")
        base_dir: Parent directory containing all repos.
                  Defaults to two levels up from this module's directory.

    Returns:
        Absolute path to the repo directory.
    """
    env_var = _REPO_ENV_VARS.get(name, name.upper().replace("-", "_") + "_PATH")

    # Tier 1: repos.env file
    if env_var in _repos_env_cache:
        return _repos_env_cache[env_var]

    # Tier 2: OS environment variable
    env_val = os.environ.get(env_var, "")
    if env_val:
        return env_val

    # Tier 3: Default relative path
    if base_dir == None:
        base_dir = os.path.join(_module_dir, "..", "..")  # stoat-community/dev/../.. = Projects/

    default_dir = _REPO_DEFAULTS.get(name, name)
    return os.path.join(base_dir, default_dir)
