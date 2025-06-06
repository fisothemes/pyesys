import asyncio
from dataclasses import dataclass
from pyesys import event


@dataclass
class Order:
    id: int
    amount: float


class OrderProcessor:
    @event
    def order_processed(self, order: Order): ...

    @order_processed.emitter
    def process_order(self, order: Order):
        print(f"Processing order #{order.id} for £{order.amount:.2f}...")


class EmailService:
    async def send_confirmation(self, order: Order):
        await asyncio.sleep(0.05)
        print(f"[Email] Sent confirmation for order #{order.id} (£{order.amount:.2f})")


class DatabaseService:
    async def record_order(self, order: Order):
        await asyncio.sleep(0.05)
        print(f"[DB] Order #{order.id} recorded with amount £{order.amount:.2f}")


class WarehouseService:
    async def notify_fulfilment(self, order: Order):
        await asyncio.sleep(0.05)
        print(f"[Warehouse] Packing team notified for order #{order.id}")


async def main():
    # Instantiate services
    email_service = EmailService()
    db_service = DatabaseService()
    warehouse_service = WarehouseService()

    # Set up processor and subscribers
    processor = OrderProcessor()
    processor.order_processed += [
        email_service.send_confirmation,
        db_service.record_order,
        warehouse_service.notify_fulfilment,
    ]

    # Simulate processing
    order = Order(123, 99.99)
    processor.process_order(order)

    # Give time for async handlers to run in background
    await asyncio.sleep(0.2)


asyncio.run(main())
