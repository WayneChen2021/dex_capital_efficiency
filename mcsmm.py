from typing import List, Tuple
from imarketmaker import MarketMakerInterface
from inputtx import InputTx
from outputtx import OutputTx
from poolstatus import MultiTokenPoolStatus

class MCSMM(MarketMakerInterface):
    def __init__(self, pairwise_pools: List[Tuple[str, str]], pairwise_infos: List[Tuple[float, float, float]], 
    single_pools: List[str], single_infos: List[Tuple[float, float]]):
        """
        Creates a multi token constant sum liquidity pool market maker

        Parameters:
        1. single_pools: specifies tokens in liquidity pool
        2. single_infos: specifies starting token balances
        3. pairwise_pools: irrelevant (for pairwise pool market makers)
        4. pairwise_info: irrelevant (for pairwise market makers)
        """
        super().__init__(pairwise_pools, pairwise_infos, single_pools, single_infos)

    def arbitrage(self, lim: float = 1e-8) -> Tuple[None, None]:
        """
        Performs no arbitrage since it is impossible on MCSMM

        Returns:
        1. 2 empty lists
        """
        return [], []

    def swap(self, tx: InputTx, out_amt: float = None) -> Tuple[OutputTx, MultiTokenPoolStatus]:
        """
        Initiate a swap specified by tx

        Parameters:
        1. tx: transaction
        2. out_amt: specifies the amount of output token removed

        Returns:
        1. output information associated with swap (after_rate is incorrect)
        2. status of pool ater swap
        """
        p = self.prices[tx.outtype] / self.prices[tx.intype]
        if out_amt == None:
            if (tx.inval / p > self.token_info[tx.outtype][0]):
                out_amt = 0
                tx.inval = 0
            else:
                out_amt = tx.inval / p

        output_tx, pool_stat = super().swap(tx, out_amt)
        output_tx.after_rate = p

        return output_tx, pool_stat