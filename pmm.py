from typing import List, Tuple
from imarketmaker import MarketMakerInterface
from inputtx import InputTx
from outputtx import OutputTx
from poolstatus import PairwiseTokenPoolStatus
import json

class PMM(MarketMakerInterface):
    def __init__(self, pairwise_pools: List[Tuple[str, str]],
    pairwise_infos: List[Tuple[float, float, float]], single_pools = None, single_infos = None):
        """
        Creates a PMM pairwise liquidity pool market maker

        Parameters:
        1. pairwise_pools: specifies pairwise liquidity pools
        2. pairwise_infos: specifies liquidity pool starting token balances
        3. single_pools: irrelevant (for multi token market makers)
        4. single_infos: irrelevant (for multi token market makers)
        """
        super().__init__(pairwise_pools, pairwise_infos, single_pools, single_infos)

    def __solveLong(self, x: float, l_e: float, s_e: float, p: float, k: float
    ) -> float:
        """
        Given the balance of the token in shortage, finds the corresponding balance
        of the token in excess

        Parameters:
        1. x: shortage token balance
        2. s_e: shortage token equilibrium balance
        3. p: exchange rates in units of excess tokens / shortage tokens
        4. k: k parameter between 2 token types


        Returns:
        1. excess token balance
        """
        return l_e - p * (x - s_e) * (1 - k + k * s_e / x)
    
    def __solveShort(self, y: float, L: float, S: float, p: float, k: float
    ) -> float:
        """
        Given the balance of the token in excess, finds the corresponding balance
        of the token in shortage

        Parameters:
        1. y: excess token balance
        2. L: excess token equilibrium balance
        3. p: exchange rates in units of excess tokens / shortage tokens
        4. k: k parameter between 2 token types

        Returns:
        1. shortage token balance
        """
        return (y-L-p*S+2*k*p*S-(y**2-2*y*L+L**2-2*y*p*S+4*k*y*p*S+2*L*p*S-4*k*L*p*S+p**2*S**2)**0.5)\
            /(2*(-1+k)*p)
    
    def swap(self, tx: InputTx, out_amt: float = None, execute: bool = True
    ) -> Tuple[OutputTx, PairwiseTokenPoolStatus]:
        """
        Initiate a swap specified by tx given that the amount of output token removed
        is known

        Parameters:
        1. tx: transaction
        2. out_amt: specifies the amount of output token removed
        3. execute: whether or not to execute the swap
        
        Returns:
        1. output information associated with swap (after_rate is incorrect)
        2. status of pool ater swap
        """
        pool = (tx.intype, tx.outtype)
        i_0 = self.token_info[pool][0]
        o_0 = self.token_info[pool][1]
        in_e, out_e = self.calculate_equilibriums(tx.intype, tx.outtype)
        k = self.token_info[pool][2]
        
        if out_amt == None:
            d = tx.inval
            p = self.prices[tx.outtype] / self.prices[tx.intype]

            if o_0 / out_e > i_0 / in_e:
                s_e, l_e = in_e, out_e
                static_amt = s_e - i_0

                if static_amt < d:
                    new_pt = self.__solveShort(d - static_amt + s_e, s_e, l_e, p, k)
                else:
                    new_pt = self.__solveLong(i_0 + d, l_e, s_e, 1/p, k)
            else:
                s_e, l_e = out_e, in_e
                new_pt = self.__solveShort(i_0 + d, l_e, s_e, p, k)
        
        if out_amt == None:
            output_tx, pool_stat = super().swap(tx, o_0 - new_pt, execute)
        else:
            output_tx, pool_stat = super().swap(tx, out_amt, execute)
        
        if execute:
            self.equilibriums[pool] = [in_e, out_e, k]
            self.equilibriums[(tx.outtype, tx.intype)] = [out_e, in_e, k]

            o, _ = self.swap(tx, None, False)
            try:
                output_tx.after_rate = tx.inval / \
                    (o.outpool_init_val - o.outpool_after_val)
            except ZeroDivisionError:
                pass
        
        return output_tx, pool_stat

    def calculate_equilibriums(self, intype: str, outtype: str) -> Tuple[float, float]:
        """
        Calculates and returns equilibrium balances

        Parameters:
        1. intype: input token type
        2. outtype: output token type

        Returns:
        1. equilibrium balance for input token
        2. equilibrium balance for output token
        """
        firstIsLong = True
        pool = (intype, outtype)
        if self.token_info[pool][0] / self.equilibriums[pool][0] >= \
            self.token_info[pool][1] / self.equilibriums[pool][1]:
            l_b = self.token_info[pool][0]
            s_b = self.token_info[pool][1]
            l_e = self.equilibriums[pool][0]
            p = self.prices[pool[1]] / self.prices[pool[0]]
        else:
            l_b = self.token_info[pool][1]
            s_b = self.token_info[pool][0]
            l_e = self.equilibriums[pool][1]
            p = self.prices[pool[0]] / self.prices[pool[1]]
            firstIsLong = False

        k = self.token_info[pool][2]
        s_e = s_b+s_b/(2*k)*((1+(4*k*(l_b-l_e))/(s_b*p))**0.5-1)

        if firstIsLong:
            return l_e, s_e
        else:
            return s_e, l_e
