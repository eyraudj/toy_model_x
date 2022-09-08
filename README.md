# Exchange Simulation

Description of the solution. See below the original [technical assignement](./README.md#Technical Assignment)
The 4 components have been implemented as expected.
On top of that, the market object and the run_exchange script have been implemented.

The prices and quantities have been assumed to be integers instead of decimals.

## Run Exchange
It is the main entry point. Either via console input or file input.
Some parameters can be set when executing the script. See console help for details.

To run it interactively:

```bash
$ python ./run_exchange.py --interactive True
```

It instantiates market and call its execution on incoming message in string format.  
-> See message section for more details of the format.

For more details about the parameterization of the exchange see the bash manual.


```bash
$ python ./run_exchange.py --help
```

## Market
It gathers the parametrization of the market, instantiates the LOB, runs some sanity checks.
The execution of the messages and first step deserialization is performed here.
See --help for more cues on parameters.

## Message
Implemented as an abstract class ``Message`` which is inherited by:
* ``AddMessage``
* ``ModifyMessage``
* ``DeleteMessage``

The full deserialization from message as str to ``Message`` objects is performed within the constructor of each class.

Format examples:
* ``A-S-12-240``
* ``A-B-1-1340``
* ``M-dsf4s64313-8``
* ``D-dsfdsg4313``
* ``D-12``
* ``M-13``

## Order Side
Just an enum representation of types of ``Order``. Stand-alone file to facilitate module imports and avoid circular calls.

## Order
Mostly container of the following data: 
* order_id
* side
* quantity 
* price

Generates its own order id (either from incrementation of previous order or from random string generation).
The order_id are returned within the console.

It can be init from an ``AddMessage``

## Limit Order Book
Implemented using a ``Dict`` to access in **O(1)** an ``Order``  object from its ``order_ids`` and, using 2 ``SortedDict``(price level -> ``deque`` of ``Order``)
for the LOB updating, one for each side (Ask and Bid).

The ``Dict`` is a Hash Table: operations are done in **O(1)**.
The ``SortedDict`` is a sort of Binary Tree: operations are done in **O(log(#elements))**.

``deque`` is double entry queue that is implemented as a doubly-linked list: search and access are done in **O(#elements)** while pure deletion and insertion (without finding the element) are done in **O(1)**. 

See https://grantjenks.com/docs/sortedcontainers/sorteddict.html

If **n** is the number of price levels and **k** the number of orders on average in each 
price level, then **m = 2 k n** is the total number of orders in the LOB.

The operations of adding, deleting, and getting from an index from the ``SortedDict`` are done in **O(log(n))**.
Whereas getting from the key, ie from the price level, is done in **O(1)**.

Because of rule of the LOB, adding a new order without any matching mechanism is hence done in **O(log(n))**. 
Deletion of an order or Modification with a higher quantity, is done in **O(k log(n)) < O(m)**.
A simple modification is done in O(1).


*Note*: This part of the algo could be arguably improved by using pointers from the hash table to the queue.
Thus, we skip the search process in the deque which is the bottle neck here done in O(k).
However, given the nature of the task and the python language, I felt to leave this unoptimised.
I felt that the pointer manipulation could actually create more burden than expected in term of performance.

An addition implying matching is done in O(k n) in the worst case.


The **matching engine** is implemented in the method:

```python
_match(self, msg: AddMessage, orderbook_side, add_method) -> Tuple[int, str]:
```
Matching is done in **O(m)** in the worst case as the entire bid or ask side could be consumed by an order.
This is the bottleneck of the algo.

Below, for reference, the technical assignment.

---

# Technical Assignment

## Introduction
In this assignment, the goal is to build a prototype of an exchange, with its basic functionality. In the essence, an exchange has the capabilities of:
* Receiving messages from the actors of the market (market makers and aggressors)
* Keeping an up-to-date LOB (level order book)
* Matching (when possible) buyers & sellers and execute trades

You’re asked to implement a simple framework with 4 components.

## Components

### Messages
Exchange should expect 3 messages (Add, Delete, Modify). Your goal is to find a suitable data structure to send necessary order messages to exchange. Messages should contain following fields:
#### Add Message:
This is a message from a market actor to place a new order and its required fields are:
* Side (Buy or Sell)
* Price
* quantity
#### Delete Message:
This is a message from a market actor to delete an existing order and its required fields are:
* Order id
#### Modify Message:
* This is a message from a market actor to modify the quantity of an existing order and its required fields are:
* Order id 
* New quantity

### Orders
Exchange should keep all distinct orders at individual Order objects. Receipt of an Add message should generate a new Order object and assign a unique Order id to it. Receipt of a Delete and Modify message should access the respective Order object (identified with its Order id) and either delete or modify it. Please note that a modify message with a higher quantity than the original would cause losing the priority of the order.

### Order Book
Exchange should build an LOB, based on price & priority (FIFO). You’re asked to use a suitable data structure that contains Order objects. Order book should allow users to access all orders at a given price level & side; ordered by their priorities. Order with an earlier arrival has a priority over a later order at the same price level. 

Example Order Book:

In the below exemplary order book, quantity 0 corresponds to the orders with the earliest arrival and hence the priority in case of an execution.

| quantity n |  ...  | quantity 2 | quantity 1 | quantity 0 | Bid Price | Ask Price | quantity 0 | quantity 1 | quantity 2 |  ...  | quantity n | 
|:--------:|:-----:|:--------:|:--------:|:--------:|:---------:|:---------:|:--------:|:--------:|:--------:|:-----:|:--------:|
|   ...    |  ...  |    30    |    20    |    40    |    *9*    |   *10*    |    5     |   100    |    70    |  ...  |   ...    |
|   ...    |  ...  |    20    |    20    |    30    |    *8*    |   *11*    |    40    |    50    |    30    |  ...  |   ...    |
|   ...    |  ...  |    5     |    50    |    50    |    *7*    |   *12*    |    20    |    10    |    60    |  ...  |   ...    |

			

### Matching Engine
Matching engine should execute any matching trades and update the LOB. After each message (when processing and LOB update is finalized), the matching engine should observe the LOB and take trade execution actions; if it exists.

Example Execution:

Using the same exemplary order book above, if a new sell order at price of 9 and quantity of 55 arrives to exchange, the matching engine should fully fill the bid at 9 with quantity of 40 (at quantity 0) and partially fill the bid at quantity 1 (15 is filled and 5 is remaining). The Order object should then be modified to contain the correct quantity after the partial fill.

## Tasks

* Implement a simplistic framework, containing above components with an object-oriented programming language of your choice. Please note that efficiency & performance of your code will be evaluated.
* Write a script that generates dummy messages and sends these messages to your exchange. There is no need to use real-market data and therefore you can make an imaginary market.
* Assess the performance of your code theoretically (for each distinct message received and for executions), by means of Big O notation. Comment on the bottlenecks on each cycle.
* Stress-test your framework with a heavily liquid order book. You may assume 100 price levels at both sides with 2000 orders at each level. Measure and compare processing time of different messages on some random orders.

## Bonus Task   

On your liquid order book, implement a function to calculate the equilibrium mid-market price (EP) which is the equilibrium price of cumulative discounted total volume functions of bid and ask side; given the parameter of half-life. 

EP is defined as follows:

```
f_bid (price)=〖g(f〗_bid (price-Δ),Δ,halflife) +TotalBidquantity(price)  
f_ask (price)=〖g(f〗_ask (price+Δ),Δ,halflife) +TotalAskquantity(price)  
f_bid (EP) = f_ask (EP)
```

Initial conditions:

```
f_bid (lowestBidPrice) =TotalBidquantity(lowestBidPrice) 
f_ask (highestAskPrice) =TotalAskquantity(highestAskPrice) 
```

Exponential Decay function:
```
g(prevVal,Δ,halflife) = ExponentialDecayFunction
```

Example decay function outputs:
``` 
g(10,1,1) = 5
g(10,2,1) = 2.5 
```

Good luck!
---

