from rongwei_plugin.models import LeadInput
from rongwei_plugin.schema_utils import tool_parameters_schema


def test_tool_schema_inlines_nested_definitions():
    schema = tool_parameters_schema(LeadInput)
    serialized = str(schema)
    assert "$ref" not in serialized
    assert "$defs" not in serialized
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert "facts" in schema["properties"]
    assert "evidence" in schema["properties"]
