# ~/ClientFactory/src/clientfactory/clients/managed/base.py
from __future__ import annotations
import typing as t
from clientfactory.resources.base import Resource, MethodConfig
from clientfactory.session.base import BaseSession
from clientfactory.transformers.base import TransformPipeline
from clientfactory.clients.managed.core import Operation, ManagedResourceConfig
from loguru import logger as log

class ManagedResource(Resource):
    """
    Resource implementation with managed operations support.
    Extends base Resource to handle CRUD and custom operations.
    """
    def __init__(self,
                 session: BaseSession,
                 config: ManagedResourceConfig,
                 resourcecls: t.Optional[t.Type] = None,
                 clientconfig: t.Optional["ClientConfig"] = None,
                 pipeline: t.Optional[TransformPipeline] = None
                ):
        super().__init__(
            session=session,
            config=config,
            resourcecls=resourcecls,
            clientconfig=clientconfig,
            pipeline=pipeline
        )
        self.operations = config.operations
        self.__setupops__()

    def __setupops__(self):
        """Configure standard and custom operations"""
        log.debug(f"ManagedResource.__setupops__ | setting up operations for {self._config.name}")

        for name, op in self.operations.operations.items():
            if not hasattr(self, name):
                methodcfg = MethodConfig(
                    name=name,
                    method=op.method,
                    path=op.path,
                    preprocess=op.preprocess,
                    postprocess=op.postprocess
                )
                self._config.methods[name] = methodcfg
                setattr(self, name, self.__methodize__(methodcfg))
                log.debug(f"ManagedResource.__setupops__ | created operation method: {name}")
