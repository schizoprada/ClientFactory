# ~/ClientFactory/src/clientfactory/utils/requests/batch.py
import time, typing as t
from dataclasses import dataclass, field
from clientfactory.utils.requests.base import RequestUtil, RequestUtilConfig
from loguru import logger as log

@dataclass
class BatchConfig(RequestUtilConfig):
    """Batch processor configuration"""
    size: int = 10
    delay: float = 1.0 # delay between batches
    stoponfail: bool = False
    collectfailed: bool = True # collect failures for retry

@dataclass
class BatchProcessor(RequestUtil):
    """Process large parameter sets in controlled batches"""
    resource: t.Callable
    params: dict[str, t.List]
    config: BatchConfig = field(default_factory=BatchConfig)

    def __post_init__(self):
        lengths = {len(v) for v in self.params.values()}
        if len(lengths) > 1:
            raise ValueError(f"All parameter lists must be equal in length. Got lengths: {lengths}")

    def __enter__(self):
        log.debug(f"BatchProcessor.__enter__ | initializing batch processor")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.debug(f"BatchProcessor.__exit__ | closing batch processor")
        pass

    def _processbatch(self, batch: dict) -> tuple[list, list]:
        successes, failures = [], []
        for params in zip(*[batch[k] for k in self.params.keys()]):
            paramdict = dict(zip(self.params.keys(), params))
            try:
                result = self.resource(**paramdict)
                successes.append((paramdict, result))
            except Exception as e:
                log.error(f"BatchProcessor._processbatch | exception processing params[{paramdict}] | {str(e)}")
                failures.append((paramdict, e))
                if self.config.stoponfail:
                    raise e
                continue
        return successes, failures

    def process(self) -> tuple[list, list]:
        log.info(f"BatchProcessor.process | starting batch processing")
        allsuccesses, allfailures = [], []

        totalitems = len(next(iter(self.params.values())))
        for start in range(0, totalitems, self.config.size):
            batch = {
                k: v[start:start + self.config.size]
                for k, v in self.params.items()
            }
            log.debug(f"BatchProcessor.process | processing batch[{start}:{start + self.config.size}]")
            successes, failures = self._processbatch(batch)
            allsuccesses.extend(successes)
            if failures:
                allfailures.extend(failures)
                if self.config.stoponfail:
                    break
            if (start+self.config.size) < totalitems:
                log.debug(f"BatchProcessor.process | sleeping for [{self.config.delay}s]")
                time.sleep(self.config.delay)
        return allsuccesses, allfailures
