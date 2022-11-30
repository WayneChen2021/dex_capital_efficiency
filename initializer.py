from typing import List, Dict, Tuple
import random
from copy import deepcopy

class Initializer():
    def __init__(self, constant: float, k: float, cap_limit: float, random_k: str = "False"):
        """
        Calculates a fair starting balance for all market makers (all token pools
        start at an equilibrium point)

        Parameters:
        1. constant: "size" each token balance should be
        2. k: k value for each pool
        3. cap_limit: maximum market cap of any token
        4. random_k: whether or not to use random k for each pool
        """
        self.constant = constant
        self.k = k
        self.cap_limit = cap_limit
        self.random_k = random_k == "True"
        self.traffic_info, self.price_gen_info = None, None
        self.pairwise_pools, self.pairwise_infos, self.single_pools, \
            self.single_infos, self.crash_types = [], [], [], [], []
    
    def configure_tokens(self, token_infos: Dict[str, Dict[str, Dict[str, float]]]):
        """
        Adds in initialization data for if some tokens are crashing

        Parameters:
        1. token_infos: contains token data for if non default values should be
        used; of the form:
        {
            "traffic_gen": {
                "LUNA": {
                    "intype_percent": 0.45,
                    "outtype_percent": 0.05,
                    "amt_mean": 10000,
                    "amt_stdv": 2000,
                    "amt_max": 20000
                },
                "UST": {
                    "intype_percent": 0.5,
                    "outtype_percent": 0.05,
                    "amt_mean": 15000,
                    "amt_stdv": 2000,
                    "amt_max": 20000
                }
            },
            "price_gen": {
                "LUNA": {
                    "start": 83,
                    "mean": -0.0005,
                    "stdv": 0.00025,
                    "change_probability": 0.99
                },
                "UST": {
                    "start": 1,
                    "mean": -0.0075,
                    "stdv": 0.00025,
                    "change_probability": 0.05
                },
                "BTC": {
                    "start": 23004
                }
            }
        }
        """
        self.traffic_info = token_infos["traffic_gen"]
        self.price_gen_info = token_infos["price_gen"]
        
        price_info = {i : self.price_gen_info[i]["start"] for i in self.price_gen_info}
        self.crash_types = [i for i in self.price_gen_info if \
            ("mean" in self.price_gen_info[i] and self.price_gen_info[i]["mean"] < 0)]
        tokens = list(price_info.keys())
        base = tokens[0]
        num_tokens = len(price_info)
        respective_prices = {}
        self.constant = self.constant ** len(self.price_gen_info)
        
        for i in price_info:
            if i != base:
                price = price_info[i] / price_info[base]
                respective_prices[i] = price
                self.constant *= price
        self.constant = self.constant ** (1/num_tokens)

        for i in respective_prices:
            price_info[i] = self.constant / respective_prices[i]
        price_info[base] = self.constant

        num_pools = num_tokens / 2
        self.single_pools = list(price_info.keys())
        self.single_infos = [[i] for i in price_info.values()]
        token_k = {}
        
        for i, tok1 in enumerate(tokens):
            for tok2 in tokens[i:]:
                pool = [tok1, tok2]
                reverse_pool = [tok2, tok1]
                self.pairwise_pools.append(pool)
                self.pairwise_pools.append(reverse_pool)
                
                pool_balances = [price_info[tok1] / num_pools, price_info[tok2] / num_pools]
                reverse_pool_balances = [pool_balances[1], pool_balances[0]]
                self.pairwise_infos.append(pool_balances)
                self.pairwise_infos.append(reverse_pool_balances)

                if self.random_k:
                    token_k[tok1] = random.randrange(1, 1000) / 1000
                    token_k[tok2] = random.randrange(1, 1000) / 1000
                else:
                    token_k[tok1] = self.k
                    token_k[tok2] = self.k
        
        for i, pool in enumerate(self.pairwise_pools):
            self.pairwise_infos[i].append((token_k[pool[0]] + token_k[pool[1]]) / 2)
        
        for i, tok in enumerate(self.single_pools):
            self.single_infos[i].append(token_k[tok])

    def get_stats(self
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[float, float, float]],
        List[str], List[Tuple[float, float]], Dict[str, Dict[str, float]],
        Dict[str, Dict[str, float]], List[str]]:
        """
        Get initialization information for market makers

        Returns:
        1. list of pairwise token pools
        2. balance and k values for pairwise token pools
        3. list of tokens
        4. balance and k values for single tokens
        5. token information for traffic generator
        6. token information for price generator
        7. token types that are crashing
        8. maximum token market cap
        """
        
        return self.pairwise_pools, self.pairwise_infos, self.single_pools, \
            self.single_infos, self.traffic_info, self.price_gen_info, self.crash_types, self.cap_limit