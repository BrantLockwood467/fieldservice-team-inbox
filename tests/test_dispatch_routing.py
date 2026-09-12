from fieldservice_inbox.work_order_router import WorkOrderContact, build_inbox_message


def test_unassigned_work_order_is_marked_for_dispatch_and_follow_up() -> None:
    contact = WorkOrderContact(
        work_order_id="WO-1842",
        customer_name="Mina Park",
        customer_email="mina@example.com",
        service_address="18 Harbor Street",
        issue="Outdoor unit is making a grinding sound.",
        dispatch_status="unassigned",
        work_order_photos=["https://example.com/work-orders/WO-1842/unit.jpg"],
        technician_follow_up=True,
    )

    message = build_inbox_message(contact)

    assert message.subject == "[ACTION REQUIRED] Work order WO-1842"
    assert "Dispatch: assign a technician." in message.text
    assert "Follow-up: technician response requested." in message.text
    assert "https://example.com/work-orders/WO-1842/unit.jpg" in message.text

