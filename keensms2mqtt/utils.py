from urllib.parse import urlsplit, urlunsplit


def host_root_url(host):
    """Builds root URL fro a hostname, using http as default scheme e.g.:
    - example.com -> http://example.com/
    - https://example.com -> https://example.com/
    """
    parts = urlsplit(host)
    scheme = parts.scheme or "http"
    netloc = parts.netloc or host
    return urlunsplit((scheme, netloc, "/", "", ""))


def deep_merge(dict1, dict2):
    """Recursively merge 2 dictionaries (used for merging default config with settings
    from config file)"""
    result = {}

    all_keys = set(dict1.keys()).union(dict2.keys())
    for key in all_keys:
        value1 = dict1.get(key)
        value2 = dict2.get(key)

        value1_is_dict = issubclass(type(value1), dict)
        value2_is_dict = issubclass(type(value2), dict)

        if value1_is_dict:
            value1 = {**value1}

        if value2_is_dict:
            value2 = {**value2}

        if value1_is_dict and value2_is_dict:
            result[key] = deep_merge(value1, value2)
        else:
            result[key] = value2 if value2 is not None else value1

    return result
