import numpy as np
from typing import Optional

from limit_order_book import LimitOrderBook
from message import Message, AddMessage, DeleteMessage, ModifyMessage

class Borg:
    """
       Abstract class which assists the implementation of singletons. See Alex Martelli's explanation.
       https://www.oreilly.com/library/view/python-cookbook/0596001673/ch05s23.html
    """
    _shared_state = {}

    def __init__(self):
        self.__dict__ = self._shared_state

    @property
    def already_initialised(self):
        return bool(self._shared_state)


class Market(Borg):
    """
    Market is a class which decodes strings into the correct Message object.
    During the encoding process sanity checks are performed.
    Singleton i.e. one instance per runtime.
    Decode messages.

    TODO - JE: decimal package to be more generic instead of using ints.
    TODO - JE: Maybe the sanity checks can be improved here.
    """

    __MESSAGE_FACTORY = {
        'A': AddMessage,
        'D': DeleteMessage,
        'M': ModifyMessage,
    }

    def __init__(
            self,
            interactive,
            price_increment: int = 1,
            quantity_increment: int = 1,
            min_price: int = None,
            max_price: int = None,
            min_quantity: int = None,
            max_quantity: int = None,
            run_sanity_checks: bool = False,
            is_random_order_id: bool = False,
    ):

        # For singleton design pattern
        Borg.__init__(self)

        if not self.already_initialised:

            self._price_increment: int = price_increment
            self._quantity_increment: int = quantity_increment
            self._min_price: int = min_price if min_price else 0
            self._max_price: int = max_price if max_price else np.inf
            self._min_quantity: int = min_quantity if min_quantity else 0
            self._max_quantity: int = max_quantity if max_quantity else np.inf
            self._run_sanity_checks: bool = run_sanity_checks

            self._limit_order_book: LimitOrderBook = LimitOrderBook(
                price_increment=self._price_increment,
                quantity_increment=self._quantity_increment,
                min_price=self._min_price,
                max_price=self._max_price,
                order_id_count=1 if not is_random_order_id else None,
            )

        self._interactive = interactive

        if self._interactive:
            print(self._limit_order_book.to_str())

    def decode(self, msg_str: str) -> Optional[Message]:
        msg_chars = msg_str.split('-')
        if msg_chars[0] not in self.__MESSAGE_FACTORY:
            if self._interactive:
                print(f'Message Type not in {self.__MESSAGE_FACTORY.keys()}')
            return

        message = self.__MESSAGE_FACTORY[msg_chars[0]](msg_chars)

        if self._run_sanity_checks:
            return self._sanity_checks(message)

        return message

    def _sanity_checks_add_message(self, msg: AddMessage) -> Optional[AddMessage]:
        if not msg or not msg.is_init:
            return

        if self._min_price > msg.price or self._max_price < msg.price:
            if self._interactive:
                print(f'Message has a price {msg.price} outside boundaries ({self._min_price} ; {self._max_price})')
            return

        if msg.price % self._price_increment:
            if self._interactive:
                print(
                    f'Message has a price {msg.price} outside the ticks. Should be an increment of {self._price_increment}'
                )
            return

        if self._min_quantity > msg.quantity or self._max_quantity < msg.quantity:
            if self._interactive:
                print(f'Message has an quantity {msg.quantity} outside boundaries [{self._min_quantity} ; {self._max_quantity}]')
            return

        if msg.quantity % self._quantity_increment:
            if self._interactive:
                print(
                    f'Message has an quantity {msg.quantity} outside the ticks. '
                    f'Should be an increment of {self._quantity_increment}'
                )
            return

        return msg

    def _sanity_checks_delete_message(self, msg: DeleteMessage) -> Optional[DeleteMessage]:
        if not msg or not msg.is_init:
            return
        return msg

    def _sanity_checks_modify_message(self, msg: ModifyMessage) -> Optional[ModifyMessage]:
        if not msg or not msg.is_init:
            return

        if self._min_quantity > msg.quantity or self._max_quantity < msg.quantity:
            if self._interactive:
                print(f'Message has an quantity {msg.quantity} outside boundaries [{self._min_quantity} ; {self._max_quantity}]')
            return

        if msg.quantity % self._quantity_increment:
            if self._interactive:
                print(
                    f'Message has an quantity {msg.quantity} outside the ticks. '
                    f'Should be an increment of {self._quantity_increment}'
                )
            return

        return msg

    def _sanity_checks(self, msg: Message):
        if isinstance(msg, AddMessage):
            self._sanity_checks_add_message(msg)
        elif isinstance(msg, DeleteMessage):
            self._sanity_checks_delete_message(msg)
        elif isinstance(msg, ModifyMessage):
            self._sanity_checks_modify_message(msg)

    def execute(self, msg: Message):
        if self._interactive:
            print(msg.encode())
        ret = self._limit_order_book.process(msg)
        if self._interactive:
            print(self._limit_order_book.send_result(msg, ret))
            print(self._limit_order_book.to_str())

    def get_lob_eq_mid(self):
        if not self._limit_order_book._order_ids_by_asks or not self._limit_order_book._order_ids_by_bids:
            return "One side of the LOB is empty - Can't compute mid"
        return self._limit_order_book.equilibrium_mid(self._limit_order_book._price_increment / 5.)
