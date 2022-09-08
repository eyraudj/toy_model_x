"""
Exchange simulator:
Captures participant messages via console or file.
We assume prices and quantities are int.
"""
import sys
import argparse
from market import Market


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--fleet_file', type=str, required=False, help='The path to an input file')
    parser.add_argument('--price_increment', type=int, required=False, default=1, help='Tick Size')
    parser.add_argument('--quantity_increment', type=int, required=False, default=1, help='Minimum change of Order quantity')
    parser.add_argument('--min_price', type=int, required=False, help='Minimum Price')
    parser.add_argument('--max_price', type=int, required=False, help='Maximum Price')
    parser.add_argument('--min_quantity', type=int, required=False, help='Minimum Order quantity')
    parser.add_argument('--max_quantity', type=int, required=False, help='Maximum Order quantity')
    parser.add_argument('--sanity_checks', required=False, default=False, action='store_true', help='Sanity Checks')
    parser.add_argument(
        '--random_order_id', required=False, default=False, action='store_true',
        help=(
            'Order IDs can be generated using uuid strings or just an incremented int starting at 1. '
            'If this flag is added, it will yield he former solution. If not, the latter.'
        )
    )
    parser.add_argument(
        '--interactive', required=False, default=False, action='store_true',
        help=(
            'Input messages via console or not. Even if a fleet file is input, '
            'the interactive console will run after by default.'
        )
    )

    args = parser.parse_args()

    print('Opening Exchange')

    if args.fleet_file:
        run_file_exchange(args)

    if args.interactive:
        run_interactive_exchange(args)

    print('Closing Exchange')

def run_file_exchange(args):
    fleet_file = args.fleet_file

    market = Market(
        interactive=False,
        price_increment=args.price_increment,
        quantity_increment=args.quantity_increment,
        min_price=args.min_price,
        max_price=args.max_price,
        min_quantity=args.min_quantity,
        max_quantity=args.max_quantity,
        run_sanity_checks=args.sanity_checks,
        is_random_order_id=args.random_order_id,
    )

    with open(fleet_file, 'r') as f:
        for msg_str in f:
            run_exchange(False, market, msg_str)

    print(f'EP: {market.get_lob_eq_mid()}')

def run_interactive_exchange(args):
    market = Market(
        interactive=True,
        price_increment=args.price_increment,
        quantity_increment=args.quantity_increment,
        min_price=args.min_price,
        max_price=args.max_price,
        min_quantity=args.min_quantity,
        max_quantity=args.max_quantity,
        run_sanity_checks=args.sanity_checks,
        is_random_order_id=args.random_order_id,
    )
    while True:
        msg_str = input()
        run_exchange(True, market, msg_str)


def run_exchange(is_interactive, market, msg_str):
    if msg_str:
        msg = market.decode(msg_str=msg_str)
        if msg and msg.is_init:
            market.execute(msg)
        else:
            if is_interactive:
                print('Something wrong with message input.')


if __name__ == '__main__':
    ret = main()
    sys.exit(ret)
