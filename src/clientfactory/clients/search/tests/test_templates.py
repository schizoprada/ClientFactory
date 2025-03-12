# ~/ClientFactory/src/clientfactory/clients/search/tests/test_templates.py
import pytest
from clientfactory.clients.search.core import Parameter, NestedParameter
from clientfactory.clients.search.templates import PayloadTemplate

def test_template_basic():
    template = PayloadTemplate(
        structure={
            "query": Parameter(name="q"),
            "page": Parameter(name="p", default=1)
        }
    )

    payload = template.generate()
    assert "query" in payload.parameters
    assert "page" in payload.parameters
    assert payload.parameters["page"].default == 1

def test_template_nested_structure():
    template = PayloadTemplate(
        structure={
            "filters": {
                "price": {
                    "min": Parameter(name="price.gte"),
                    "max": Parameter(name="price.lte")
                }
            }
        }
    )

    payload = template.generate()
    assert isinstance(payload.parameters["filters"], NestedParameter)
    assert "min" in payload.parameters["filters"].children["price"].children
    assert "max" in payload.parameters["filters"].children["price"].children

def test_template_defaults():
    template = PayloadTemplate(
        structure={
            "filters": {
                "price": {
                    "min": Parameter(name="price.gte"),
                    "max": Parameter(name="price.lte")
                }
            }
        },
        defaults={
            "filters.price.min": 0,
            "filters.price.max": 1000
        }
    )

    payload = template.generate()
    assert payload.parameters["filters"].children["price"].children["min"].default == 0
    assert payload.parameters["filters"].children["price"].children["max"].default == 1000

def test_template_required():
    template = PayloadTemplate(
        structure={
            "query": Parameter(name="q"),
            "page": Parameter(name="p")
        },
        required=["query"]
    )

    payload = template.generate()
    assert payload.parameters["query"].required == True
    assert payload.parameters["page"].required == False

def test_template_inheritance():
    base = PayloadTemplate(
        structure={
            "query": Parameter(name="q", required=True)
        }
    )

    extended = base.extend(
        structure={
            "page": Parameter(name="p", default=1)
        }
    )

    payload = extended.generate()
    assert "query" in payload.parameters
    assert "page" in payload.parameters
    assert payload.parameters["query"].required == True
    assert payload.parameters["page"].default == 1

def test_template_override():
    template = PayloadTemplate(
        structure={
            "query": Parameter(name="q", default=""),
            "page": Parameter(name="p", default=1)
        }
    )

    # Test overriding defaults during generation
    payload = template.generate(
        query=Parameter(name="q", default="shoes"),
        page=Parameter(name="p", default=2)
    )

    assert payload.parameters["query"].default == "shoes"
    assert payload.parameters["page"].default == 2

def test_multiple_inheritance():
    base = PayloadTemplate(
        structure={"query": Parameter(name="q")},
        defaults={"query": ""}
    )

    filters = base.extend(
        structure={"filters": {"price": Parameter(name="price")}}
    )

    pagination = filters.extend(
        structure={"page": Parameter(name="p")},
        defaults={"page": 1}
    )

    payload = pagination.generate()
    assert all(k in payload.parameters for k in ["query", "filters", "page"])
    assert payload.parameters["page"].default == 1
