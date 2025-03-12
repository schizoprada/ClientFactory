# ~/ClientFactory/src/clientfactory/utils/requests/chain.py
import typing as t
from dataclasses import dataclass, field
from clientfactory.utils.requests.base import RequestUtil, RequestUtilConfig
from loguru import logger as log

@dataclass
class ChainConfig(RequestUtilConfig):
    """Chain processor configuration"""
    xkey: t.Optional[str] = None  # key to extract from response
    stoponfail: bool = True

@dataclass
class ChainLink:
    """Single link in request chain"""
    resource: t.Callable
    params: t.Union[dict, t.Callable]
    config: t.Optional[ChainConfig] = None

@dataclass
class RequestChain(RequestUtil):
    """Chain multiple requests with dependencies"""
    links: list[ChainLink] = field(default_factory=list)
    config: ChainConfig = field(default_factory=ChainConfig)

    def __enter__(self):
        log.debug(f"RequestChain.__enter__ | initializing request chain")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.debug(f"RequestChain.__exit__ | closing request chain")
        pass

    def add(self, resource: t.Callable, params: t.Union[dict, t.Callable], config: t.Optional[ChainConfig]=None) -> 'RequestChain':
        """Add link to chain"""
        self.links.append(ChainLink(resource, params, (config or self.config)))
        return self

    def __matmul__(self, link: tuple[t.Callable, t.Union[dict, t.Callable], t.Optional[ChainConfig]]) -> 'RequestChain':
        """Operator syntax for adding links: chain @ (resource, params, config)"""
        resource, params, *config = link  # Unpack config if provided
        return self.add(resource, params, config[0] if config else None)

    def __call__(self) -> list[tuple[dict, t.Any]]:
        """Execute chain via call operator"""
        return self.execute()

    def execute(self) -> list[tuple[dict, t.Any]]:
        """Execute chain of requests"""
        log.info(f"RequestChain.execute | executing chain of [{len(self.links)}] requests")
        results = []
        lastresult = None

        for i, link in enumerate(self.links):
            log.debug(f"RequestChain.execute | processing link[{i}]")
            try:
                # Initialize params before try block to avoid unboundlocal
                params = {}
                params = (
                    link.params(lastresult) if callable(link.params)
                    else link.params
                )

                result = link.resource(**params)

                if link.config and link.config.xkey:
                    result = result.get(link.config.xkey)

                results.append((params, result))
                lastresult = result

            except Exception as e:
                log.error(f"RequestChain.execute | error in link[{i}]: {str(e)}")
                results.append((params, e))
                if link.config and link.config.stoponfail:
                    raise e

        return results
