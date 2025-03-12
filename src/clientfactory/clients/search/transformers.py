# ~/ClientFactory/src/clientfactory/clients/search/transformers.py
import urllib.parse, typing as t
from clientfactory.transformers.base import (
    Transform,
    TransformType,
    TransformOperation,
    MergeMode,
    DEFAULT
)
from loguru import logger as log

class PayloadTransform(Transform):
    def __init__(
        self,
        key: str,
        valmap: dict,
        order: int = 0,
        nestkey: bool = False,
        excludekeys: t.Optional[list] = [],
        mergemode: (str | MergeMode) = MergeMode.UPDATE
    ):
        super().__init__(
            type=TransformType.PAYLOAD,
            operation=TransformOperation.MERGE,
            target=key,
            order=order
        )
        self.key = key
        self.valmap = valmap
        self.nestkey = nestkey
        self.excludekeys = excludekeys
        self.mergemode = mergemode if isinstance(mergemode, MergeMode) else MergeMode(mergemode)

    def deepmerge(self, target: dict, source: dict) -> dict:
        result = target.copy()
        for k, v in source.items():
            if k in result:
                if isinstance(v, dict) and isinstance(result[k], dict):
                    result[k] = self.deepmerge(result[k], v)
                elif (result[k] is not None) or (v is None):
                    continue
                else:
                    result[k] = v
        return result

    def apply(self, value: dict, context: dict = DEFAULT.CONTEXT()) -> dict:
        log.debug(f"PayloadTransform.apply | input: {value}")
        structure = {
            k: v for k, v in self.valmap.items()
            if k not in self.excludekeys
        }

        processedkeys = context.get('processed', set())
        transformhistory = context.get('history', [])

        if self.mergemode == MergeMode.NESTEDONLY:
            merged = value.copy()
            if (self.key in merged) and (self.key not in processedkeys):
                if merged[self.key] is None: merged[self.key] = {}
                merged[self.key] = self.deepmerge(merged[self.key], structure)
                processedkeys.add(self.key)
            else:
                merged[self.key] = structure.copy()
                processedkeys.add(self.key)
        elif self.mergemode == MergeMode.ROOTONLY:
            merged = structure.copy()
            unprocessed = {k:v for k,v in value.items() if (k!=self.key) and (k not in processedkeys)}
            merged = self.deepmerge(merged, unprocessed)
            processedkeys.update(merged.keys())
        else: # update (default behavior)
            merged = structure.copy()
            if self.key and self.nestkey:
                if self.key in merged:
                    if merged[self.key] is None: merged[self.key] = {}
                    merged[self.key] = self.deepmerge(merged[self.key], structure)
                else:
                    merged[self.key] = structure.copy()
                processedkeys.add(self.key)
            else:
                merged = self.deepmerge(merged, structure)
            processedkeys.update(merged.keys())

        context['processed'] = processedkeys
        transformhistory.append(self.__class__.__name__)
        context['history'] = transformhistory

        result = {
            k:v for k,v in merged.items()
            if v is not None
        }
        log.debug(f"PayloadTransform.apply | output: {result}")
        log.debug(f"PayloadTransform.apply | context: {context}")
        return result


class URLTransform(Transform):
    def __init__(self, key:str, baseurl: str, order: int = 1):
        super().__init__(
            type=TransformType.URL,
            operation=TransformOperation.MAP,
            target=key,
            order=order
        )
        self.key = key
        self.baseurl = baseurl

    def apply(self, value: dict) -> dict:
        log.debug(f"URLTransform.apply | input: {value}")
        url = f"{self.baseurl}?{urllib.parse.urlencode(value)}"
        result = {"url": url}  # Return dict with URL instead of just URL
        log.debug(f"URLTransform.apply | output: {result}")
        return result


class ProxyTransform(Transform):
    """Transform for proxy-style APIs"""
    def __init__(
                self,
                apiurl: str,
                key: str = "proxy",
                valmap: dict = {"url": "url"},
                order: int = 2,
                **kwargs
            ):
        super().__init__(
            type=TransformType.PARAMS,
            operation=TransformOperation.MAP,
            target=key,
            order=order
        )
        self.apiurl = apiurl
        self.valmap = valmap
        self.kwargs = kwargs

    def apply(self, value: dict) -> dict:
        log.debug(f"ProxyTransform.apply | input: {value}")
        log.debug(f"ProxyTransform.apply | using apiurl: {self.apiurl}")
        log.debug(f"ProxyTransform.apply | using valmap: {self.valmap}")

        # Extract URL from previous transform
        url = value.get("url")
        if not url:
            raise ValueError("Missing URL from previous transform")

        # Create proxy params
        result = {
            outkey: url if inkey == "url" else self.kwargs.get(inkey)
            for outkey, inkey in self.valmap.items()
        }
        log.debug(f"ProxyTransform.apply | output: {result}")
        return result
