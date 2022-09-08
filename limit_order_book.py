from typing import Dict, Tuple
from collections import deque
from scipy import optimize

import numpy as np
from sortedcontainers import SortedDict

from order import Order
from order_side import OrderSide
from message import Message, AddMessage, DeleteMessage, ModifyMessage


class LimitOrderBook:
    """
    We assumed an order-based LOB with Price/Time/quantity priority.
    """

    def __init__(
            self, price_increment: int = 1, quantity_increment: int = 1, min_price: int = 0, max_price: int = np.inf,
            order_id_count: int = None,
    ):
        self._price_increment: int = price_increment
        self._quantity_increment: int = quantity_increment
        self._min_price: int = min_price
        self._max_price: int = max_price
        # TODO - Complexity:
        #  Two data structures for each side of the LOB: a special hash table with keys being the price levels and
        #  the values being double-entry queues.
        #  A SortedDict is essentially a hash table with a list of keys maintained in order:
        #  Complexity of Add, Del and Get from index in O(log(n)), Get from key in O(1).
        #  n is the theoretical number of price levels.
        #  The underlying implementation might be a binary tree.
        #  See doc: https://grantjenks.com/docs/sortedcontainers/sorteddict.html

        self._order_ids_by_bids: SortedDict[int, deque] = SortedDict(lambda n: -n)  # Reversed order
        self._order_ids_by_asks: SortedDict[int, deque] = SortedDict()
        # TODO - Complexity:
        #  Hash Table. Add, Del, Get in O(1).
        self._order_by_ids: Dict[str, Order] = {}
        self._high_bid: int = self._min_price
        self._low_ask: int = self._max_price

        # Cache of order_ids to be deleted
        self._to_delete_order_ids = []

        # For sequential order id generation
        self._order_id_count = order_id_count

    def process(self, msg: Message):
        if isinstance(msg, AddMessage):
            self._process_add_message(msg)
        elif isinstance(msg, DeleteMessage):
            self._process_delete_message(msg)
        elif isinstance(msg, ModifyMessage):
            self._process_modify_message(msg)

    def _process_add_message(self, msg: AddMessage):
        if msg.side == OrderSide.BUY:
            if msg.price < self._low_ask:
                return self._bid_msg_add(msg)
            else:  # msg.price >= self._limit_order_book.low_ask
                return self._ask_match(msg)
        else:  # msg.side == OrderSide.SELL
            if msg.price > self._high_bid:
                return self._ask_msg_add(msg)
            else:  # msg.price <= self._limit_order_book.high_bid
                return self._bid_match(msg)

    def _process_delete_message(self, msg: DeleteMessage):
        # TODO - Complexity: In O(1)
        if msg.order_id not in self._order_by_ids:
            return None
        # TODO - Complexity: In O(1)
        order = self._order_by_ids[msg.order_id]

        if order.side == OrderSide.BUY:
            ret = self._bid_delete(order)

        else:  # order.side == OrderSide.SELL
            ret = self._ask_delete(order)

        del self._order_by_ids[msg.order_id]
        return ret

    def _process_modify_message(self, msg: ModifyMessage):
        if msg.order_id not in self._order_by_ids:
            return None

        order = self._order_by_ids[msg.order_id]
        quantity = order.quantity
        order.quantity = msg.quantity

        # If the new quantity is greater than the previous order quantity we place the order at the end of the queue
        if quantity < msg.quantity:
            if order.side == OrderSide.BUY:
                ret = self._bid_delete(order)
                return self._bid_order_add(order)
            else:  # order_side == OrderSide.SELL
                ret = self._ask_delete(order)
                return self._ask_order_add(order)

        # If the new quantity == 0 we simply delete the order
        if msg.quantity == 0:
            if order.side == OrderSide.BUY:
                order_id = self._bid_delete(order)
            else:  # order_side == OrderSide.SELL
                order_id = self._ask_delete(order)

            del self._order_by_ids[msg.order_id]

            return order_id

    def _ask_msg_add(self, msg: AddMessage) -> str:
        if not self._order_id_count:
            order = Order.from_msg(msg)
            order_id = self._ask_order_add(order)
        else:
            order = Order.from_msg(msg, self._order_id_count)
            order_id = self._ask_order_add(order)
            self._order_id_count = order_id

        self._order_by_ids[order_id] = order
        if msg.price < self._low_ask:
            self._low_ask = msg.price
        return order_id

    def _bid_msg_add(self, msg: AddMessage) -> str:
        if not self._order_id_count:
            order = Order.from_msg(msg)
            order_id = self._bid_order_add(order)
        else:
            order = Order.from_msg(msg, self._order_id_count)
            order_id = self._bid_order_add(order)
            self._order_id_count = order_id

        self._order_by_ids[order_id] = order
        if msg.price > self._high_bid:
            self._high_bid = msg.price
        return order_id

    def _ask_order_add(self, order: Order):
        if order.price not in self._order_ids_by_asks:
            self._order_ids_by_asks[order.price] = deque()
        self._order_ids_by_asks[order.price].append(order.order_id)
        return order.order_id

    def _bid_order_add(self, order: Order):
        if order.price not in self._order_ids_by_bids:
            self._order_ids_by_bids[order.price] = deque()
        self._order_ids_by_bids[order.price].append(order.order_id)
        return order.order_id
            
    def _ask_match(self, msg: AddMessage) -> str:

        self._low_ask, new_order_id = self._match(msg, self._order_ids_by_asks, self._bid_msg_add)
        # TODO - JE: return more info and build a data structure to keep track of fills and partial fills
        return new_order_id

    def _bid_match(self, msg: AddMessage) -> str:

        self._high_bid, new_order_id = self._match(msg, self._order_ids_by_bids, self._ask_msg_add)
        # TODO - JE: return more info and build a data structure to keep track of fills and partial fills
        return new_order_id

    def _has_price_crossed(self, target_price, price_level, side) -> bool:
        """
        Check if an incoming message price is more attractive than a price level given a side.
        :param target_price:
        :param price_level:
        :param side:
        :return: True if the price is unattractive.
        """
        # If it's a BUY the price level is not attractive if it is above the target price -> True
        # If it's a SELL the price level is not attractive if it is below the target price -> True

        if side == OrderSide.BUY:
            return target_price < price_level
        else:  # side == OrderSide.SELL
            return target_price > price_level

    def _match(self, msg: AddMessage, orderbook_side, add_method) -> Tuple[int, str]:
        """
        Matching Engine.
        Returns the updated top of the book as an int and the new order id as str if
        it is a partial fill of the incoming message.

        """
        # TODO - Complexity: The engine runs through all the orders of one side of the book so the algo
        #   complexity is in O(m) m being the total number of orders in the book, = O(k n) with k price levels and
        #   n orders per price level.

        residual_quantity, last_visited_price_level = self._consume_quantity_or_order_book(
            quantity=msg.quantity, target_price=msg.price, side=msg.side, orderbook_side=orderbook_side,
        )

        top_of_the_book, new_order_id = self._manage_partial_fill(
            residual_quantity, msg.side, orderbook_side, last_visited_price_level, add_method, msg
        )

        self._clear_delete_order_ids_cache()

        return top_of_the_book, new_order_id

    def _consume_quantity_or_order_book(self, quantity, target_price, side, orderbook_side) -> Tuple[int, int]:
        """
        :param quantity:
        :param target_price:
        :param side:
        :param orderbook_side:
        :return: quantity, last_visited_price_level
        """

        last_visited_price_level = None


        # Run through the different existing price levels of the given side of the LOB
        # TODO - Complexity: Because the SortedDict is modified while running through the keys, it takes O(log(n)),
        #   with n being the number of price levels, to pop item and reinsert at the end if needed.
        while orderbook_side:
            price_level, order_deque = orderbook_side.popitem()

            # If the price level becomes not matchable (i.e. worse of than the one in the message)
            if self._has_price_crossed(target_price=target_price, price_level=price_level, side=side):
                return quantity, last_visited_price_level

            last_visited_price_level = price_level

            # Until we consume the orderbook level
            while order_deque:
                current_order_id = order_deque.popleft()

                quantity -= self._order_by_ids[current_order_id].quantity
                self._to_delete_order_ids.append(current_order_id)

                #  The incoming order quantity can be exhausted
                if quantity <= 0:
                    if order_deque:
                        orderbook_side[price_level] = order_deque
                    return quantity, last_visited_price_level

            if order_deque:
                orderbook_side[price_level] = order_deque

        return quantity, last_visited_price_level

    def _manage_partial_fill(self, residual_quantity, side, orderbook_side, price_level, add_method, msg) -> Tuple[int, str]:
        new_order_id = None

        if residual_quantity < 0:  # partial fill of order standing in LOB, but full fill of incoming message
            order_id = self._to_delete_order_ids.pop()
            self._order_by_ids[order_id].quantity = abs(residual_quantity)
            top_of_book = self._order_by_ids[order_id].price
            if top_of_book not in orderbook_side:
                orderbook_side[top_of_book] = deque()
            orderbook_side[top_of_book].appendleft(order_id)

        else:  # quantity >= 0, partial matching of incoming message because order book empty or crossed price
            if price_level not in orderbook_side:
                if not orderbook_side:
                    top_of_book = self._get_reset_top_of_book(side=side)
                else:
                    top_of_book = orderbook_side.iloc[0]
            else:
                top_of_book = price_level

            if residual_quantity:  # quantity > 0, it's a partial fill
                msg.quantity = residual_quantity
                new_order_id = add_method(msg)

        return top_of_book, new_order_id

    def _clear_delete_order_ids_cache(self):
        # TODO - Complexity: in O(m)
        for order_id in self._to_delete_order_ids:
            del self._order_by_ids[order_id]
        self._to_delete_order_ids = []

    def _bid_delete(self, order: Order):
        """
        :param order:
        :return:
        """
        # TODO - Complexity: Remove is in O(k), k = deque length at the price level
        #  Thus O(k log(n)).
        #  We could have added pointer from order_by_order_ids to the bid to get O(1) in access,
        #  but pointer access and manipulation could have costed more during removal.
        self._order_ids_by_bids[order.price].remove(order.order_id)
        return order.order_id

    def _ask_delete(self, order: Order):
        """
        :param order:
        :return:
        """
        # TODO - Complexity: Remove is in O(k), k = deque length at the price level
        #  Thus O(k log(n))
        #  We could have added pointer from order_by_order_ids to the bid to get O(1) in access,
        #  but pointer access and manipulation could have costed more during removal.
        self._order_ids_by_asks[order.price].remove(order.order_id)
        return order.order_id

    def _get_reset_top_of_book(self, side) -> int:
        """
        Send a reseting value of top of the book ie either high bid or low ask according to the incoming message side.

        The incoming msg is a BUY, hence it consumed the ask side
        or, it is a SELL and it consumed the bid side.

        :param side: Enum
        :return: self._min_price or self._max_price
        """

        if side == OrderSide.BUY:
            return self._max_price
        else:  # msg_side == OrderSide.SELL
            return self._min_price

    def to_str(self) -> str:
        """
        String representation of the LOB. The orders are each level are not shown whereas they are managed internally.
        :return: Some LOB representation.
        """
        ret = ''
        if np.isinf(self._low_ask):
            ret += '\n ---------- Empty Asks ---------- \n'
        else:
            ret_prices = []
            ret_quantitys = []

            step = self._low_ask
            for _ in range(10):
                ret_prices.append(step)
                if step not in self._order_ids_by_asks:
                    ret_quantitys.append(0)
                    step += self._price_increment
                    continue
                ret_quantitys.append(sum([self._order_by_ids[id_].quantity for id_ in self._order_ids_by_asks[step]]))
                step += self._price_increment

            ret += f'Ask quantitys : {ret_quantitys} \n'
            ret += f'Ask Prices : {ret_prices} \n'

        if not self._high_bid:
            ret += '\n ---------- Empty Bids ---------- \n'
        else:
            ret_prices = []
            ret_quantitys = []

            step = self._high_bid
            for _ in range(10):
                ret_prices.append(step)
                if step not in self._order_ids_by_bids:
                    ret_quantitys.append(0)
                    step -= self._price_increment
                    continue
                ret_quantitys.append(sum([self._order_by_ids[id_].quantity for id_ in self._order_ids_by_bids[step]]))
                step -= self._price_increment

            ret += f'Bid quantitys : {ret_quantitys} \n'
            ret += f'Bid Prices : {ret_prices} \n'

        return ret

    def send_result(self, msg, ret) -> str:
        """
        String representation of the result of an incoming message
        :param msg:
        :param ret:
        :return:
        """
        # TODO - JE: More verbose
        if isinstance(msg, AddMessage):
            return f'Message Added {ret}'
        if isinstance(msg, DeleteMessage):
            return f'Message Deleted {ret}'
        if isinstance(msg, ModifyMessage):
            return f'Message Modified {ret}'

    def equilibrium_mid(self, half_time_ticks: float) -> float:
        """
        Needs low_ask and high_bid => mid != 0
        :param half_time_ticks: > 0
        :return: equilibrium mid within spread: Note that this quantity should be able to be outside the spread
        """
        mid = (self._low_ask + self._high_bid) / 2.

        bid_cum_q = self.cum_decaying_bid_quantity(half_time_ticks, mid)
        ask_cum_q = self.cum_decaying_ask_quantity(half_time_ticks, mid)
        diff_cum_q = lambda p: (
                2 ** (-abs(p-self._high_bid)/(mid * half_time_ticks)) * bid_cum_q
                - 2 ** (-abs(p-self._low_ask)/(mid * half_time_ticks)) * ask_cum_q
        )

        high_bound = self._low_ask
        low_bound = self._high_bid
        ret = optimize.root_scalar(
            diff_cum_q, bracket=[low_bound, high_bound], xtol=0.1 * self._price_increment, maxiter=100, method='bisect'
        )
        return ret.root

    def _cum_decaying_quantity(self, half_time_ticks: float, orderbook_side, mid: float, top_of_book: int) -> float:
        """
        Slicing make it costly to run in terms of performance
        :param price: 
        :param half_time_ticks: 
        :return: 
        """
        cum_sum = 0
        for price_level, order_id_deque in reversed(orderbook_side.items()):
            for order_id in order_id_deque:
                cum_sum += self._order_by_ids[order_id].quantity
            cum_sum *= 2 ** (-abs(price_level - top_of_book) / (half_time_ticks * mid))

        return cum_sum

    def cum_decaying_bid_quantity(self, half_time_ticks: float, mid: float) -> float:
        return self._cum_decaying_quantity(half_time_ticks, self._order_ids_by_bids, mid, self._high_bid)
    
    def cum_decaying_ask_quantity(self, half_time_ticks, mid: float) -> float:
        return self._cum_decaying_quantity(half_time_ticks, self._order_ids_by_asks, mid, self._low_ask)

