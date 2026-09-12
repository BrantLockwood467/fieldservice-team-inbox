from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, get_origin, get_type_hints

try:
    from pydantic import BaseModel, EmailStr, Field, HttpUrl
except ModuleNotFoundError:  # Keep the pure routing helper usable in minimal test environments.
    EmailStr = str
    HttpUrl = str

    def Field(default: Any = ..., *, default_factory: Any = None, **constraints: Any) -> Any:
        return default_factory() if default_factory is not None else default

    class BaseModel:
        def __init__(self, **values: Any) -> None:
            hints = get_type_hints(type(self))
            for name, annotation in hints.items():
                value = values.get(name, getattr(type(self), name, ...))
                if value is ...:
                    raise ValueError(f"{name} is required")
                origin = get_origin(annotation)
                if origin is list:
                    if not isinstance(value, list):
                        raise TypeError(f"{name} must be a list")
                    value = [str(item) for item in value]
                elif isinstance(annotation, type) and issubclass(annotation, Enum):
                    value = annotation(value)
                elif annotation is str and not isinstance(value, str):
                    raise TypeError(f"{name} must be a string")
                setattr(self, name, value)


class DispatchStatus(str, Enum):
    UNASSIGNED = "unassigned"
    DISPATCHED = "dispatched"
    ON_SITE = "on_site"


class WorkOrderContact(BaseModel):
    work_order_id: str = Field(min_length=1, max_length=80)
    customer_name: str = Field(min_length=1, max_length=120)
    customer_email: EmailStr
    service_address: str = Field(min_length=1, max_length=300)
    issue: str = Field(min_length=1, max_length=2000)
    dispatch_status: DispatchStatus
    work_order_photos: list[HttpUrl] = Field(default_factory=list, max_length=10)
    technician_follow_up: bool = False


@dataclass(frozen=True)
class InboxMessage:
    subject: str
    text: str


def build_inbox_message(contact: WorkOrderContact) -> InboxMessage:
    needs_dispatch = contact.dispatch_status == DispatchStatus.UNASSIGNED
    priority = "ACTION REQUIRED" if needs_dispatch else "FIELD UPDATE"
    dispatch_line = (
        "Dispatch: assign a technician."
        if needs_dispatch
        else f"Dispatch: {contact.dispatch_status.value.replace('_', ' ')}."
    )
    follow_up_line = (
        "Follow-up: technician response requested."
        if contact.technician_follow_up
        else "Follow-up: no technician response requested."
    )
    photo_lines = (
        "\n".join(f"- {photo}" for photo in contact.work_order_photos)
        if contact.work_order_photos
        else "- none attached"
    )
    text = "\n".join(
        [
            f"Work order: {contact.work_order_id}",
            f"Customer: {contact.customer_name} <{contact.customer_email}>",
            f"Address: {contact.service_address}",
            dispatch_line,
            follow_up_line,
            "",
            "Issue:",
            contact.issue,
            "",
            "Photos:",
            photo_lines,
        ]
    )
    return InboxMessage(
        subject=f"[{priority}] Work order {contact.work_order_id}",
        text=text,
    )
