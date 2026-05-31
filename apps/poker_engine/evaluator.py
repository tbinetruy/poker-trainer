from collections import Counter
from itertools import combinations

RANKS = "23456789TJQKA"
RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANKS)}


def evaluate_seven(cards: list[str]) -> tuple:
    if len(cards) < 5:
        raise ValueError("At least five cards are required.")

    return max(evaluate_five(list(combo)) for combo in combinations(cards, 5))


def evaluate_five(cards: list[str]) -> tuple:
    ranks = sorted((RANK_VALUE[card[0]] for card in cards), reverse=True)
    suits = [card[1] for card in cards]
    counts = Counter(ranks)
    count_groups = sorted(((count, rank) for rank, count in counts.items()), reverse=True)
    flush = len(set(suits)) == 1
    straight_high = _straight_high(ranks)

    if flush and straight_high:
        return (8, straight_high)

    if count_groups[0][0] == 4:
        quad_rank = count_groups[0][1]
        kicker = max(rank for rank in ranks if rank != quad_rank)
        return (7, quad_rank, kicker)

    if count_groups[0][0] == 3 and count_groups[1][0] == 2:
        return (6, count_groups[0][1], count_groups[1][1])

    if flush:
        return (5, *ranks)

    if straight_high:
        return (4, straight_high)

    if count_groups[0][0] == 3:
        trip_rank = count_groups[0][1]
        kickers = sorted((rank for rank in ranks if rank != trip_rank), reverse=True)
        return (3, trip_rank, *kickers)

    pairs = [rank for count, rank in count_groups if count == 2]
    if len(pairs) == 2:
        high_pair, low_pair = sorted(pairs, reverse=True)
        kicker = max(rank for rank in ranks if rank not in pairs)
        return (2, high_pair, low_pair, kicker)

    if len(pairs) == 1:
        pair = pairs[0]
        kickers = sorted((rank for rank in ranks if rank != pair), reverse=True)
        return (1, pair, *kickers)

    return (0, *ranks)


def _straight_high(ranks: list[int]) -> int | None:
    unique = sorted(set(ranks), reverse=True)
    if 14 in unique:
        unique.append(1)

    for index in range(len(unique) - 4):
        window = unique[index : index + 5]
        if window[0] - window[-1] == 4:
            return window[0]

    return None

