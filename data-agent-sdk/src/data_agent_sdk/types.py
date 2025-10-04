"""Core type definitions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4


class PermissionMode(str, Enum):
    DEFAULT = "default"
    PLAN = "plan"


@dataclass
class Artifact:
    uri: str
    format: str
    schema: Dict[str, str]
    lineage: Dict[str, Any] = field(default_factory=dict)
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "format": self.format,
            "schema": self.schema,
            "row_count": self.row_count,
        }


@dataclass
class SessionContext:
    warehouse: str
    user: str
    role: str
    catalog_uri: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class ToolUseMessage:
    tool_name: str
    tool_input: Dict[str, Any]
    tool_use_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ToolResultMessage:
    tool_use_id: str
    result: Any
    is_error: bool = False
    artifact: Optional[Artifact] = None


@dataclass
class AgentConfig:
    allowed_tools: List[str] = field(default_factory=list)
    permission_mode: PermissionMode = PermissionMode.DEFAULT
