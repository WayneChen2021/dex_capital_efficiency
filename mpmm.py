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

    def __argMin(self, s: float, l: float, k: float, p: float, S: float, L: float
    ) -> float:
        """
        Subject to the constraint of a shortage and excess token type, finds the
        an equilibrium balance for the excess token type that minimizes the distance
        to a desired equilibrium determined from the pool's initial balances

        Parameters:
        1. s: shortage token balance
        2. l: excess token balance
        3. k: k parameter between 2 token types
        4. p: exchange rates in units of excess tokens / shortage tokens
        5. S: shortage token balance at pool's initialization
        6. L: excess token balance at pool's initialization

        Returns:
        1. optimal excess token equilibrium point
        """
        t1 = 4*k*L**2*p*s*S**2
        t2 = 4*k**2*l*p**2*S**4
        t3 = 8*k**2*L*p**2*S**4
        t4 = k*p**3*s*S**4
        t5 = L**4*s**2+4*k*l*L**2*p*s*S**2
        t6 = 4*k*L**3*p*s*S**2
        t7 = L**2*p**2*s**2*S**2
        t8 = 8*k**2*l*L*p**2*S**4
        t9 = 4*k**2*L**2*p**2*S**4
        t10 = 2*k*L*p**3*s*S**4
        t11 = 1024*k**3*L**6*p**3*s**3*S**6
        t12 = 6144*k**4*l*L**4*p**4*s**2*S**8
        t13 = 6144*k**4*L**5*p**4*s**2*S**8
        t14 = 5376*k**3*L**4*p**5*s**3*S**8
        t15 = 27648*k**4*L**4*p**5*s**3*S**8
        t16 = 27648*k**5*L**4*p**5*s**3*S**8
        t17 = 27648*k**4*L**4*p**5*s**2*S**9
        t18 = 55296*k**5*L**4*p**5*s**2*S**9
        t19 = 12288*k**5*l**2*L**2*p**5*s*S**10
        t20 = 24576*k**5*l*L**3*p**5*s*S**10
        t21 = 39936*k**5*L**4*p**5*s*S**10
        t22 = 6144*k**4*l*L**2*p**6*s**2*S**10
        t23 = 6144*k**4*L**3*p**6*s**2*S**10
        t24 = 768*k**3*L**2*p**7*s**3*S**10
        t25 = 8192*k**6*l**3*p**6*S**12
        t26 = 24576*k**6*l**2*L*p**6*S**12
        t27 = 24576*k**6*l*L**2*p**6*S**12
        t28 = 8192*k**6*L**3*p**6*S**12
        t29 = 6144*k**5*l**2*p**7*s*S**12
        t30 = 12288*k**5*l*L*p**7*s*S**12
        t31 = 6144*k**5*L**2*p**7*s*S**12
        t32 = 1536*k**4*l*p**8*s**2*S**12
        t33 = 1536*k**4*L*p**8*s**2*S**12
        t34 = 128*k**3*p**9*s**3*S**12
        t35 = k**2*p**2*S**4
        x1 = t1+t2+t3+t4
        x2 = t5+t6+t7+t8+t9+t10
        x3 = t11-t12+t13+t14-t15+t16+t17-t18+t19-t20+t21+t22-t23+t24-t25+t26-t27+t28-t29+t30-t31-t32+t33-t34
        x4 = -16*x1**2+192*t35*x2
        x5 = (x3+(x3**2+4*x4**3)**0.5)**(1/3)

        ans = x1/(12*t35)+x4/(24*2**(2/3)*t35*x5)-(1/(48*2**(1/3)*t35))*x5
        if isinstance(ans, complex):
            return ans.real
        else:
            return ans
    
    def __newtonMethod(self, s: float, l: float, k: float, p: float, S: float, L: float
    ) -> float:
        """
        Subject to the constraint of a shortage and excess token type, finds the
        an equilibrium balance for the excess token type that minimizes the distance
        to a desired equilibrium determined from the pool's initial balances

        Parameters:
        1. s: shortage token balance
        2. l: excess token balance
        3. k: k parameter between 2 token types
        4. p: exchange rates in units of excess tokens / shortage tokens
        5. S: shortage token balance at pool's initialization
        6. L: excess token balance at pool's initialization

        Returns:
        1. optimal excess token equilibrium point
        """
        approx = min(s/S, l/L) * min([s, S, l, L])
        new_approx = self.__update_approx(approx, s, l, k, p, S, L)
        i = 0
        while abs(new_approx - approx) > self.float_tolerance:
            approx = new_approx
            new_approx = self.__update_approx(approx, s, l, k, p, S, L)
            i += 1
            if i >= 1000:
                print({"s": s, "l": l, "k": k, "p": p, "S": S, "L": L})
                print(1/0)

        return new_approx
    
    def __update_approx(self, x: float, s: float, l: float, k: float, p: float, S: float, L: float
    ) -> float:
        """
        Updates apprximation for long equilibrium point

        Parameters:
        1. x: current long equilibrium approximation
        2. s: shortage token balance
        3. l: excess token balance
        4. k: k parameter between 2 token types
        5. p: exchange rates in units of excess tokens / shortage tokens
        6. S: shortage token balance at pool's initialization
        7. L: excess token balance at pool's initialization

        Returns:
        1. updated long token equilibrium point
        """
        func = self.__first_deriv(x, s, l, k, p, S, L)
        deriv = self.__second_deriv(x, s, l, k, p, S, L)
        new_x = x - func / deriv
        
        while True:
            try:
                new_func = self.__first_deriv(new_x, s, l, k, p, S, L)
                new_deriv =  self.__second_deriv(new_x, s, l, k, p, S, L)
                if new_func != new_func or new_deriv != new_deriv or isinstance(new_func, complex) or isinstance(new_deriv, complex):
                    new_x = (x + new_x) / 2
                else:
                    break
            except:
                new_x = (x + new_x) / 2
        
        return new_x
    
    def __first_deriv(self, x: float, s: float, l: float, k: float, p: float, S: float, L: float
    ) -> float:
        """
        Calculates first derivative of function to minimize

        Parameters:
        1. x: current long equilibrium approximation
        2. s: shortage token balance
        3. l: excess token balance
        4. k: k parameter between 2 token types
        5. p: exchange rates in units of excess tokens / shortage tokens
        6. S: shortage token balance at pool's initialization
        7. L: excess token balance at pool's initialization

        Returns:
        1. first derivative
        """
        return (2*(1-((s*(sqrt((4*k*(l-x))/(p*s)+1)-1))/(2*k)+s)/S))/(S*p*sqrt((4*k*(l-x))/(p*s)+1))-(2*(1-x/L))/L
    
    def __second_deriv(self, x: float, s: float, l: float, k: float, p: float, S: float, L: float
    ) -> float:
        """
        Calculates second derivative of function to minimize

        Parameters:
        1. x: current long equilibrium approximation
        2. s: shortage token balance
        3. l: excess token balance
        4. k: k parameter between 2 token types
        5. p: exchange rates in units of excess tokens / shortage tokens
        6. S: shortage token balance at pool's initialization
        7. L: excess token balance at pool's initialization

        Returns:
        1. second derivative
        """
        return 2/(S**2*p**2*((4*k*(l-x))/(p*s)+1))+(4*k*(1-((s*(sqrt((4*k*(l-x))/(p*s)+1)-1))/(2*k)+s)/S))/(S*p**2*s*((4*k*(l-x))/(p*s)+1)**(3/2))+2/L**2
    
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
