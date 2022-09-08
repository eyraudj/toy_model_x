import uuid

from message import AddMessage
from order_side import OrderSide


class Order:

    def __init__(self,  order_id: str, side: OrderSide, quantity: int, price: int):
        self._order_id = order_id
        self._side: OrderSide = side
        self._quantity: int = quantity
        self._price: int = price

    @classmethod
    def from_msg(cls, msg: AddMessage, prev_order_id: int = None):
        if not prev_order_id:
            order_id = uuid.uuid4().hex
        else:
            order_id = int(prev_order_id) + 1
        return Order(
            order_id=str(order_id),
            side=msg.side,
            quantity=msg.quantity,
            price=msg.price,
        )

    @property
    def order_id(self):
        return self._order_id

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        self._quantity = value

    @property
    def price(self):
        return self._price

    @property
    def side(self):
        return self._side
