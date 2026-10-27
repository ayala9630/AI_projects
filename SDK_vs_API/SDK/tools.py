"""SDK shares the exact same domain dispatch and tool schemas as API."""
from shared.tool_schemas import TOOL_SCHEMAS
from shared.dispatch import dispatch_tool

__all__ = ["TOOL_SCHEMAS", "dispatch_tool"]
