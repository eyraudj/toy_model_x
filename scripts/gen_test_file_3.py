import numpy as np

ORDER_NUMBER = 300
FILE = '../test_data/file_test_6.txt'

def gen_message_str(ids):
    mid = 100
    price_increment = 1
    average_trade_size = 50
    volume_increment = 1

    # 50% chance of to work on each side of the book
    rand_int = np.random.randint(2)
    side = 'B' if rand_int else 'S'
    #
    sigma = mid / 25.
    coef = -1 if rand_int else 1
    price = int(mid + coef * round(np.random.normal(0, sigma)))

    quantity = int(average_trade_size / 2 + abs(round(np.random.normal(0, volume_increment*10))))

    rand_int2 = np.random.randint(3)
    type = ['A', 'M' , 'D'][rand_int2]

    if type == 'A':
        msg_str = f'{type}-{side}-{quantity}-{price}'
        ids.append(ids[-1] + 1)
    if type == 'M':
        idx = np.random.randint(round(len(ids) * 1.2))
        if idx >= len(ids):
            id_ = 'random'
        else:
            id_ = ids[idx]
        msg_str = f'{type}-{id_}-{quantity}'
    if type == 'D':
        idx = np.random.randint(round(len(ids) * 1.2))
        if idx >= len(ids):
            id_ = 'random'
        else:
            id_ = ids[idx]
        msg_str = f'{type}-{id_}'

    return msg_str

def gen_message_str_2() -> [str]:
    average_trade_size = 50
    volume_increment = 1
    ret = []
    for _idx1 in range(100):
        for _idx2 in range(2000):
            quantity = int(average_trade_size / 2 + abs(round(np.random.normal(0, volume_increment * 10))))
            ret.append(f'A-S-{quantity}-{1000 + 100 - _idx1}')

    for _idx1 in range(100):
        for _idx2 in range(2000):
            quantity = int(average_trade_size / 2 + abs(round(np.random.normal(0, volume_increment * 10))))
            ret.append(f'A-B-{quantity}-{1000 - _idx1}')

    return ret

ret = gen_message_str_2()

with open(FILE, 'a') as the_file:
    for msg_str in ret:
        the_file.write(f'{msg_str}\n')




