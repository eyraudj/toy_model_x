"""
Message Strings follow a specific format:
The first character defines the message type: A, D or M respectively for Add, Delete and Modify.


For instance AddMessage:
'A-<B or S>-<quantity>-<price>
B for Buy and S for Sell
--> 'A-B-12-240'

For instance DeleteMessage:
'D-<id>'
--> 'D-1231316'

For instance ModifyMessage:
'M-<id>-<quantity>'
--> 'M-1231316-8'

"""
from abc import ABC, abstractmethod
from typing import List
from order_side import OrderSide


class Message(ABC):

    def __init__(self, msg_chars: List[str]):
        self._is_init = False

    @abstractmethod
    def encode(self):
        pass

    @property
    def is_init(self):
        return self._is_init


class AddMessage(Message):

    def __init__(self, msg_chars: List[str]):
        super().__init__(msg_chars)
        if len(msg_chars) != 4:
            return

        self._side: OrderSide = None
        if msg_chars[1] == 'B':
            self._side = OrderSide.BUY
        elif msg_chars[1] == 'S':
            self._side = OrderSide.SELL
        else:  # msg_chars[1] not in ['B', 'S']
            return

        try:
            self._quantity: int = int(msg_chars[2])
            self._price: int = int(msg_chars[3])
        except Exception: #TODO - JE not the way but for the exercise ok
            return
        self._is_init = True

    def encode(self):
        side_str = 'B' if self._side == OrderSide.BUY else 'S'  # self._side == OrderSide.SELL
        return f'A-{side_str}-{self._quantity}-{self._price}'

    @property
    def side(self):
        return self._side

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, value):
        self._quantity = value

    @property
    def price(self):
        return self._price


class DeleteMessage(Message):

    def __init__(self, msg_chars: List[str]):
        super().__init__(msg_chars)
        if len(msg_chars) != 2:
            return
        try:
            self._order_id: str = str(msg_chars[1])
        except Exception:  # TODO - JE not the way but for the exercise ok
            return
        self._is_init = True

    def encode(self):
        return f'D-{self._order_id}'

    @property
    def order_id(self):
        return self._order_id


class ModifyMessage(Message):

    def __init__(self, msg_chars: List[str]):
        super().__init__(msg_chars)
        if len(msg_chars) != 3:
            return

        try:
            self._order_id: str = str(msg_chars[1])
            self._quantity: int = int(msg_chars[2])
        except Exception:  # TODO - JE not the way but for the exercise ok
            return
        self._is_init = True

    def encode(self):
        return f'M-{self._order_id}-{self._quantity}'

    @property
    def order_id(self):
        return self._order_id

    @property
    def quantity(self):
        return self._quantity
