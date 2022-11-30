from typing import List, Tuple
from imarketmaker import MarketMakerInterface
from inputtx import InputTx
from outputtx import OutputTx
from poolstatus import PairwiseTokenPoolStatus

class CSMM(MarketMakerInterface):
    def __init__(self, pairwise_pools: List[Tuple[str, str]],
    pairwise_infos: List[Tuple[float, float, float]], single_pools = None, single_infos = None):
        """
        Creates a constant sum pairwise liquidity pool market maker

        Parameters:
        1. pairwise_pools: specifies pairwise liquidity pools
        2. pairwise_infos: specifies liquidity pool starting token balances
        3. single_pools: irrelevant (for multi token market makers)
        4. single_infos: irrelevant (for multi token market makers)
        """
        super().__init__(pairwise_pools, pairwise_infos, single_pools, single_infos)
    
    def arbitrage(self, lim: float = 1e-8) -> Tuple[None, None]:
        """
        Performs no arbitrage since it is impossible on CSMM

        Returns:
        1. 2 empty lists
        """
        return [], []

    def swap(self, tx: InputTx, out_amt: float = None) -> Tuple[OutputTx, PairwiseTokenPoolStatus]:
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
            if (tx.inval / p > self.token_info[(tx.intype, tx.outtype)][1]):
                out_amt = 0
                tx.inval = 0
            else:
                out_amt = tx.inval / p

        output_tx, pool_stat = super().swap(tx, out_amt)
        output_tx.after_rate = p

        return output_tx, pool_stat