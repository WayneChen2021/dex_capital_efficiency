import numpy as np
import random
import os
import pandas as pd
from typing import List, Tuple, Dict
from inputtx import InputTx
from datetime import datetime, timedelta

class TrafficGenerator():
    def __init__(self, sigma: float, mean: float, arb_probability: float, shape: Tuple[int, int],
    max_price: float, is_norm: str = "True"):
        """
        Generates traffic

        Parameters:
        1. sigma: standard deviation of swap amount (in dollars)
        2. mean: mean of swap amount (in dollars)
        3. arb_probability: probability any swap should be for arbitrage
        4. shape: output shape of traffic
        5. max_price: upper bound on how much (in dollars) a swap can be
        6. is_norm: whether or not swap amounts should be normally distributed
        """
        self.mean = mean
        self.sigma = sigma
        self.arb_probability = [1 - arb_probability, arb_probability]
        self.batches = shape[0]
        self.batch_size = shape[1]
        self.max_price = max_price
        self.is_norm = is_norm == "True"
        self.token_list = None
        self.token_info = None
        self.intype_probabilities = []
        self.outtype_probabilities = []
    
    def configure_tokens(self, token_list: List[str], token_info: Dict[str, Dict[str, float]],
    cap_limit: float):
        """
        Configures parameters related to tokens

        Parameters:
        1. token_list: list of tokens
        2. token_info: contains token data for if non default values should be
        used; of the form:
        {   
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
        }
        3. cap_limit: maximum market cap of any token
        """
        self.cap_limit = cap_limit
        self.token_list = token_list
        self.token_info = token_info
        tokens = len(token_list)
        self.intype_probabilities = [0] * tokens
        self.outtype_probabilities = [0] * tokens
        
        custom_ins, custom_outs = 0, 0
        for i, tok in enumerate(token_list):
            if tok in token_info:
                info = token_info[tok]
                if "intype_percent" in info:
                    self.intype_probabilities[i] = info["intype_percent"]
                    custom_ins += 1
                if "outtype_percent" in info:
                    self.outtype_probabilities[i] = info["outtype_percent"]
                    custom_outs += 1
        
        remainder = tokens - custom_ins
        if remainder:
            avg = (1 - sum(self.intype_probabilities)) / remainder
            for i, percent in enumerate(self.intype_probabilities):
                if not percent:
                    self.intype_probabilities[i] = avg
        
        remainder = tokens - custom_outs
        if remainder:
            avg = (1 - sum(self.outtype_probabilities)) / remainder
            for i, percent in enumerate(self.outtype_probabilities):
                if not percent:
                    self.outtype_probabilities[i] = avg

    def __get_amt(self, intype: str, price: float, token_infos: Dict[str, Tuple[float, float]]) -> float:
        """
        Given the token price, generates a swap amount

        Parameters:
        1. intype: deposit token type
        2. price: token price
        3. token_infos: contains values for estimating intype market cap and current
        balance in marketmaker

        Returns:
        1. token swap amount
        """
        sigma = self.sigma
        mean = self.mean
        max_price = self.max_price
        if intype in self.token_info:
            info = self.token_info[intype]
            if "amt_stdv" in info:
                sigma = info["amt_stdv"]
            if "amt_mean" in info:
                mean = info["mean"]
            if "amt_max" in info:
                max_price = info["amt_max"]
        
        if self.is_norm:
            deviation = np.random.normal(0, sigma)
            while deviation <= -1 * mean:
                deviation = np.random.normal(0, sigma)
            
            amt_dols = min((deviation + mean), max_price)
        else:

            amt_dols = random.randrange(0, max_price * 1000) / 1000
        
        market_cap = self.cap_limit * token_infos[intype][0]
        if token_infos[intype][1] * price > market_cap:
            print('traced')
            return 0
        return amt_dols / price
    
    def __get_pair(self) -> Tuple[str, str]:
        """
        Randomly picks 2 tokens to swap between

        Returns:
        1. input token type
        2. output token type
        """
        intype = random.choices(self.token_list, weights=self.intype_probabilities, k=1)[0]
        outtype = random.choices(self.token_list, weights=self.outtype_probabilities, k=1)[0]
        while outtype == intype:
            outtype = random.choices(self.token_list, weights=self.outtype_probabilities, k=1)[0]
        
        return intype, outtype

    def generate_traffic(self, prices: List[Tuple[datetime, Dict[str, float]]], load_true_data: bool = False) -> List[List[InputTx]]:
        """
        Generates traffic

        Parameters:
        1. prices: details token prices at each batch; of the form:
        {
            "BTC": 23004,
            "UST": 1
        }

        Returns:
        1. list of batches of swaps
        """
        def sample_token(token_probs: Dict[str, float]):
            in_out_pairs = []
            weights = []
            for tok_1 in token_probs.keys():
                for tok_2 in token_probs.keys():
                    if tok_1 != tok_2:
                        in_out_pairs.append((tok_1, tok_2))
                        weights.append(token_probs[tok_1] * token_probs[tok_2])

            in_type, out_type = random.choices(in_out_pairs, weights, k=1)[0]
            
            return in_type, out_type

        txs = []
        if not load_true_data:
            choices = [0,1]
            prices = [tup[1] for tup in prices]
            token_infos = {tok: [1,0] for tok in prices[0]}
            for batch in range(self.batches):
                batch_txs = []
                for tx in range(self.batch_size):
                    amt = 0
                    while amt == 0:
                        intype, outtype = self.__get_pair()
                        token_infos[intype][0] = prices[batch][intype] / prices[0][intype]
                        amt = self.__get_amt(intype, prices[batch][intype], token_infos)
                    
                    arb = random.choices(choices, self.arb_probability) == [1]
                    batch_txs.append(InputTx(intype, outtype, amt, arb))               
                    token_infos[intype][1] += amt
                    token_infos[outtype][1] -= amt * prices[batch][intype] / prices[batch][outtype]

                txs.append(batch_txs)
        else:
            timestamp_strings_to_volumes = {}
            for volume_csv in os.listdir('true_data/daily_volumes'):
                ticker = volume_csv[: volume_csv.index('-')].upper()
                volumes = pd.read_csv(f'true_data/daily_volumes/{volume_csv}')
                for _, row in volumes.iterrows():
                    timestmap_string = str((datetime.strptime(row['snapped_at'][: -4], '%Y-%m-%d %H:%M:%S') + timedelta(days=1)).date())
                    if not timestmap_string in timestamp_strings_to_volumes:
                        timestamp_strings_to_volumes[timestmap_string] = {ticker: float(row['total_volume'])}
                    else:
                        timestamp_strings_to_volumes[timestmap_string][ticker] = float(row['total_volume'])
            
            for idx, (timestamp, price_infos) in enumerate(prices):
                volume = timestamp_strings_to_volumes[str(timestamp.date())]
                token_in_amounts = {}
                token_out_amounts = {}
                batch_txs = []
                for _ in range(self.batch_size):
                    in_type, out_type = sample_token(volume)
                    sampled_amt = np.random.normal(self.mean, self.sigma)
                    amt = float(np.clip(sampled_amt, 0, self.max_price) / price_infos[in_type])
                    batch_txs.append(InputTx(in_type, out_type, amt, random.choices([0, 1], self.arb_probability) == [1]))

                    token_in_amounts[in_type] = amt if not in_type in token_in_amounts else amt + token_in_amounts[in_type]
                    token_out_amounts[out_type] = amt if not out_type in token_out_amounts else amt + token_out_amounts[out_type]

                txs.append(batch_txs)
                # import pdb; pdb.set_trace()

        return txs