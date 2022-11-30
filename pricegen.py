from typing import List, Dict
from copy import deepcopy
import random
import numpy as np

class PriceGenerator():
    def __init__(self, mean: float, stdv: float, change_probability: float, batches: int):
        """
        Generates prices for each batch in the traffic; price percentage changes are normally distributed

        Parameters:
        1. mean: average percent price change between batches
        2. stdv: standard deviation of percent price changes between batches
        3. change_probability: probability of any token's price changing between batches
        4. batches: number of batches in traffic
        """
        self.batches = batches
        self.mean = mean
        self.stdv = stdv
        self.probabilities = [1 - change_probability, change_probability]

    def configure_tokens(self, token_info: Dict[str, Dict[str, float]]):
        """
        Configures parameters related to tokens

        Parameters:
        1. token_info: contains token data for if non default values should be
        used; of the form:
        {
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
        """
        self.token_info = token_info
    
    def __get_new_price(self, token: str, old_price: float) -> float:
        """
        Generates new price for token

        Parameters:
        1. token: token type
        2. old_price: token's old price

        Returns:
        1. new price for token type
        """
        mean = self.mean
        stdv = self.stdv
        probability = self.probabilities
        info = self.token_info[token]
        if "mean" in info:
            mean = info["mean"]
        if "stdv" in info:
            stdv = info["stdv"]
        if "change_probability" in info:
            val = info["change_probability"]
            probability = [1 - val, val]
        
        if random.choices([0,1], probability) == [1]:

            return (1 + mean + np.random.normal(0, stdv)) * old_price
        else:
            return old_price
    
    def simulate_ext_prices(self) -> List[Dict[str, float]]:
        """
        Generates prices for each batch in the traffic; price percentage changes are normally distributed

        Returns:
        1. prices for each batch of swaps
        """
        batch_price = {i : self.token_info[i]["start"] for i in self.token_info}
        prices = [deepcopy(batch_price)]

        for batch in range(self.batches - 1):
            for tok in batch_price:
                batch_price[tok] = self.__get_new_price(tok, batch_price[tok])

            prices.append(deepcopy(batch_price))
        
        return prices