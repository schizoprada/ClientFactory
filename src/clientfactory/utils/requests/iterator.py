# ~/ClientFactory/src/clientfactory/utils/requests/iterator.py
import time, enum, typing as t, itertools as it
from dataclasses import dataclass, field
from contextlib import contextmanager
from clientfactory.utils.requests.base import RequestUtil, RequestUtilConfig
from loguru import logger as log


@dataclass
class ParamIterator:
    """Single parameter iteration configuration"""
    name: str
    start: t.Optional[t.Any] = None
    end: t.Optional[t.Any] = None
    step: t.Optional[t.Any] = 1
    values: t.Optional[t.Iterable] = None

    def __post_init__(self):
        if (self.values is None) and (any(v is None for v in [self.start, self.end])):
            raise ValueError(f"Must provide either values lsit or start/end for param [{self.name}]")

        # convert values to list:
        if (self.values) and (not isinstance(self.values, list)):
            self.values = list(self.values)

    def generate(self) -> t.Iterator:
        if self.values is not None:
            yield from self.values
        else:
            current = self.start
            while current <= self.end:
                yield current
                current += self.step

    def __call__(self):
        return self.generate()


class IteratorStrategy(enum.Enum):
    PRODUCT = "product"
    ZIP = "zip"
    CHAIN = "chain"



@dataclass
class IteratorConfig(RequestUtilConfig):
    """Iterator specific configuration"""
    strategy: (IteratorStrategy | str) = IteratorStrategy.PRODUCT
    params: t.Dict[str, ParamIterator] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.strategy, IteratorStrategy): # convert strings to iterator strategies
            try:
                self.strategy = IteratorStrategy(self.strategy)
            except ValueError:
                raise ValueError(f"IteratorConfig | {self.strategy} is not valid strategy | valid: {list(IteratorStrategy)}")


class Iterator(RequestUtil):
    """Multi-parameter request iterator"""

    def __init__(self, resource: t.Callable, params: t.Dict[str, (ParamIterator | dict)], strategy: (str | IteratorStrategy) = IteratorStrategy.PRODUCT, config: t.Optional[RequestUtilConfig] = None):
        super().__init__(config)
        self.resource = resource
        self.params = {
            name: (param if isinstance(param, ParamIterator) else ParamIterator(name=name, **param))
            for name, param in params.items()
        }
        self.config = IteratorConfig(
            strategy=strategy,
            params=self.params,
            **(config.__dict__ if config else {})
        )
        log.debug(f"Iterator.__init__ | initialized | strategy: {strategy} | params: {params}")

    def __enter__(self):
        log.debug(f"Iterator.__enter__ | entering context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.debug(f"Iterator.__exit__ | exiting context")
        pass

    def _iterproduct(self) -> t.Iterator[dict]:
        """Cartesian product of all parameter values"""
        paramvalues = {
            name: list(param.generate())
            for name, param in self.params.items()
        }
        paramnames = list(paramvalues.keys())

        for values in it.product(*[paramvalues[name] for name in paramnames]):
            yield dict(zip(paramnames, values))

    def _iterzip(self) -> t.Iterator[dict]:
        """Zip parameters together"""
        paramiters = {
            name: param.generate()
            for name, param in self.params.items()
        }
        paramnames = list(paramiters.keys())
        for values in zip(*[paramiters[name] for name in paramnames]):
            yield dict(zip(paramnames, values))

    def _iterchain(self) -> t.Iterator[dict]:
        """Chain parameter iterations sequentially"""
        for name, param in self.params.items():
            for value in list(param.generate()):
                yield {name: value}


    def iterate(self, **kwargs) -> t.Iterator[tuple[dict, t.Any]]:
        """Iterate over parameter combinations"""
        for name, values in kwargs.items():
            if name in self.params:
                self.params[name].values = values
                log.debug(f"Iterator.iterate | updated values for param[{name}]: {values}")

        iterstrat = self.config.strategy.value.lower() if isinstance(self.config.strategy, IteratorStrategy) else self.config.strategy.lower()
        iterator = getattr(self, f"_iter{iterstrat}", self._iterproduct)() # default fallback just so my IDE doesnt have an aneurysm for now
        log.info(f"Iterator.iterate | starting iteration strategy: {self.config.strategy}")

        for params in iterator:
            log.debug(f"Iterator.iterate | requesting with params: {params}")
            try:
                result = self.resource(**params)
                time.sleep(self.config.delay)
                yield params, result
            except Exception as e:
                log.error(f"Iterator.iterate | error making request: {str(e)}")
                if self.config.raiseonerror:
                    raise
