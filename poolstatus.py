from typing import List, Dict, Tuple

class PoolStatusInterface:
    def __init__(self):
        raise NotImplementedError

class MultiTokenPoolStatus(PoolStatusInterface, dict):
    def __init__(self, status: Dict[str, Tuple[float, float]]):
        """
        Represents pool status for multi token liquidity pool market makers with
        computable k

        Parameters:
        1. status: dictionary indicating tokens' counts and min k value
        """
        dict.__init__(self, status)


class PairwiseTokenPoolStatus(PoolStatusInterface, dict):
    def __init__(self, token_pairs: List[Tuple[str, str]],
    token_infos: List[Tuple[float, float, float]]):
        """
        Represents pool status for 2 token liquidity pool market makers

        Parameters:
        1. token_pairs: tuples of trading pairs, i.e "['BTC. 'ETH']"; should not 
        have redundant pairs
        2. token_infos: token counts and k values for each trading pair
        """
        for (tokenA, tokenB), (amountA, amountB, k) in zip(token_pairs, token_infos):
            self[(tokenA, tokenB)] = [amountA, amountB, k]
