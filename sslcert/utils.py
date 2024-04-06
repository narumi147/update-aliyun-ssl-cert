import functools
import json

from alibabacloud_cas20200407 import models as cas_models
from alibabacloud_tea_openapi import models as open_api_models

from .logger import logger


def dump_json(obj, indent=None) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=indent)


def validate_tea_resp(response):
    try:
        # not really ListUserCertificateOrderResponse
        resp: cas_models.ListUserCertificateOrderResponse = response
        resp.validate()
        if resp.status_code != 200:
            raise Exception("not 200")
        logger.info(f"response body: {dump_json(resp.body.to_map())}")
    except:
        logger.exception(f"response validate failed: {dump_json(resp.to_map())}")
        raise


def _try_dump_tea_model(model: open_api_models.TeaModel):
    if model is None:
        return str(model)
    try:
        return dump_json(model.to_map())
    except:
        return str(model)


def print_aliapi_params(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        param_list: list[str] = []
        for v in args[1:]:
            param_list.append(_try_dump_tea_model(v))
        for k, v in kwargs.items():
            param_list.append(f"{k}: {_try_dump_tea_model(v)}")
        content = "\n".join([f"  - {param}" for param in param_list])

        if args:
            func_name = args[0].__class__.__name__ + "." + func.__name__
        else:
            func_name = func.__qualname__

        logger.debug(f"API '{func_name}' called with params:\n{content}".strip())

        return func(*args, **kwargs)

    return wrapper
