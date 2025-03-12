# ~/ClientFactory/src/clientfactory/clients/search/templates.py
import typing as t
from dataclasses import dataclass, field
from clientfactory.clients.search.core import Parameter, NestedParameter, Payload
from loguru import logger as log


@dataclass
class PayloadTemplate:
    """Template for creating reusable payload configurations"""
    structure: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    parent: t.Optional['PayloadTemplate'] = None

    def __post_init__(self):
        self._parameters = self._buildparams(self.structure)

    def _buildparams(self, structure: dict) -> dict:
        """convert dictionary structure to parameter objects"""
        parameters = {}
        for k, v in structure.items():
            if isinstance(v, (Parameter, NestedParameter)):
                parameters[k] = v
            elif isinstance(v, dict):
                parameters[k] = NestedParameter(
                    name=k,
                    children=self._buildparams(v)
                )
            else:
                parameters[k] = Parameter(name=k, default=v)
        return parameters

    def extend(self, **kwargs) -> 'PayloadTemplate':
        """create a new template extending this one"""
        return PayloadTemplate(
            structure={**self.structure, **kwargs.get('structure', {})},
            defaults={**self.defaults, **kwargs.get('defaults', {})},
            required=[*self.required, *kwargs.get('required', [])],
            parent=self
        )

    def generate(self, **overrides) -> Payload:
        parameters = {}
        if self.parent:
            parameters.update(self.parent._parameters)
        parameters.update(self._parameters)

        for k, v in self.defaults.items():
            if '.' in k:
                parts = k.split('.')
                current = parameters
                for part in parts[:-1]:
                    if part not in current:
                        continue
                    if isinstance(current[part], NestedParameter):
                        current = current[part].children
                    else:
                        break
                if parts[-1] in current:
                    current[parts[-1]].default = v
            else:
                if k in parameters:
                    parameters[k].default = v

        for k in self.required:
            if k in parameters:
                parameters[k].required = True

        for k, v in overrides.items():
            if k in parameters:
                if isinstance(v, (Parameter, NestedParameter)):
                    parameters[k] = v
                else:
                    parameters[k].default = v

        return Payload(parameters=parameters)
