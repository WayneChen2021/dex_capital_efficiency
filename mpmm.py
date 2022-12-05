from typing import List, Tuple
from imarketmaker import MarketMakerInterface
from inputtx import InputTx
from outputtx import OutputTx
from poolstatus import MultiTokenPoolStatus
from copy import deepcopy
from math import sqrt

class MPMM(MarketMakerInterface):
    def __init__(self, pairwise_pools: List[Tuple[str, str]], pairwise_infos: List[Tuple[float, float, float]], 
    single_pools: List[str], single_infos: List[Tuple[float, float]]):
        """
        Creates a multi token PMM based liquidity pool market maker

        Parameters:
        1. single_pools: specifies tokens in liquidity pool
        2. single_infos: specifies starting token balances
        3. pairwise_pools: irrelevant (for pairwise pool market makers)
        4. pairwise_info: irrelevant (for pairwise market makers)
        """
        super().__init__(pairwise_pools, pairwise_infos, single_pools, single_infos)
        self.float_tolerance = 1e-5
    
    def getK(self, intype: str, outtype: str) -> float:
        """
        Defines k parameter for token pairs

        Parameters:
        1. intype: input token type
        2. outtype: output token type

        Returns:
        1. k value
        """
        return max(self.token_info[intype][1], self.token_info[outtype][1])

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
        k = self.getK(intype, outtype)
        p = self.prices[outtype] / self.prices[intype]
        lst = []
        I, O = self.equilibriums[intype][0], self.equilibriums[outtype][0]

        in_0, out_0 = self.token_info[intype][0], self.token_info[outtype][0]
        lst.append(((in_0, out_0), self.__distSq(I, O, in_0, out_0)))

        in_1, out_1 = self.__getEquilibrium(intype, outtype, k, 1 / p)
        if not(isinstance(in_1, complex) or isinstance(out_1, complex)):
            if (in_1 + self.float_tolerance >= in_0 and out_0 + self.float_tolerance >= out_1) or \
                (out_1 + self.float_tolerance >= out_0 and in_0 + self.float_tolerance >= in_1):
                lst.append(((in_1, out_1), self.__distSq(I, O, in_1, out_1)))

        out_2, in_2 = self.__getEquilibrium(outtype, intype, k, p)
        if not(isinstance(in_2, complex) or isinstance(out_2, complex)):
            if (in_2 + self.float_tolerance >= in_0 and out_0 + self.float_tolerance >= out_2) or \
                (out_2 + self.float_tolerance >= out_0 and in_0 + self.float_tolerance >= in_2):
                lst.append(((in_2, out_2), self.__distSq(I, O, in_2, out_2)))

        lst = sorted(lst, key=lambda x: x[1])

        return lst[0][0][0], lst[0][0][1]
    
    def __getEquilibrium(self, short: str, long: str, k: float, p: float) -> Tuple[float, float]:
        """
        Calculates and returns equilibrium balances given a short and long token type

        Parameters:
        1. short: shortage token type
        2. long: excess token type

        Returns:
        1. equilibrium balance for shortage token type
        2. equilibrium balance for excess token type
        """
        s = self.token_info[short][0]
        l = self.token_info[long][0]
        l_e = self.__argMin(s, l, k, p, self.equilibriums[short][0], self.equilibriums[long][0])

        return s + s / (2*k) * ((1 + (4*k * (l - l_e)) / (s * p))**0.5 - 1), l_e

    def __distSq(self, x0: float, y0: float, x1: float, y1: float) -> float:
        """
        Calculates how far a pair of token balance are from the desired equilibrium
        determined from the pool's initial balances

        Parameters:
        1. x0: token type 1's balance at the pool's initialization
        2: y0: token type 2's balance at the pool's initialization
        3. x1: token type 1's current balance
        4. y1: token type 2's current balance

        Returns:
        1. distance token balances are from the desired equilibrium
        """
        return (1 - x1 / x0) ** 2 + (1 - y1 / y0) ** 2

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
        1. Shortage token balance
        """
        return (y-L-p*S+2*k*p*S-(y**2-2*y*L+L**2-2*y*p*S+4*k*y*p*S+2*L*p*S-4*k*L*p*S+p**2*S**2)**0.5)\
            /(2*(-1+k)*p)

    def swap(self, tx: InputTx, out_amt: float = None, execute: bool = True
    ) -> Tuple[OutputTx, MultiTokenPoolStatus]:
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
        i_0, o_0 = self.token_info[tx.intype][0], self.token_info[tx.outtype][0]
        in_e, out_e = self.calculate_equilibriums(tx.intype, tx.outtype)
        if out_amt == None:
            d = tx.inval
            k = self.getK(tx.intype, tx.outtype)
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
            o, _ = self.swap(tx, None, False)
            try:
                output_tx.after_rate = tx.inval / \
                    (o.outpool_init_val - o.outpool_after_val)
            except ZeroDivisionError:
                pass
        
        return output_tx, pool_stat
