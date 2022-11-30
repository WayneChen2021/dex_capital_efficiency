# multi-token-proactive-market-maker

run the code: ```python simulator.py```

note: This is a continuation of a group project from summer 2022, and I am now working on it by myself.

# Introduction

While most cryptocurrency trading is facilitated by centralized platforms like Binance, there has recently been significant development in decentralized alternatives, particularly those that employ an automated system. This is in part due to a lack of liquidity: there are not enough buyers and sellers to constantly fill orders in an order book system. On the other hand, automated systems ensure swaps can always take place quickly.

These automated decentralized exchanges, commonly referred to as automated market makers, are implemented as smart contracts on blockchains that users can swap tokens with. Tokens are provided by liquidity providers and live in two token pools for swapping. Liquidity providers are typically required to deposit some amount of both token types in a ratio determined by a pool’s parameter. In return for their deposit, they earn transaction fees.

Ideally, users would be able to swap at rates similar to that of the market rate (i.e. the rate derived from dividing 2 tokens' prices with respect to some traditional currency). The token pools should also have non-changing token balances over time, so liquidity providers can remove their token deposits without incurring losses. Related to this, it should be impossible to completely drain any one of the token’s supply in a pool.

# Constant product: the baseline

The most common automated market makers employ a constant product formula. It maintains that the product of token balances in a pool always remains constant. Another way to observe this relation is visualizing the pool state as the equation $y=C/x$, where $C$ is the constant, and $x$ and $y$ are the token balances.

The exchange rate at any point is given by $\frac{\partial y}{\partial x}$. Since $\frac{\partial y}{\partial x}$ is strictly increasing (from negative infinity to 0), there is exactly 1 pool state where the exchange rate matches the market rate. Due to arbitrage, this becomes an equilibrium point and the pool state is most often somewhere nearby at any time. Assuming the market exchange rate between $x$ and $y$ does not change and the pool state starts at equilibrium, then the constant product model keeps the pool state steady near this equilibrium. The pool can be initialized to start at equilibrium by having the first liquidity provider deposit amounts of both token types in proportion to the tokens’ prices.

Also notice that $x$ and $y$ can never reach 0, as that would require an infinite amount of the other token. So, no token’s supply can be entirely removed.

Finally, for pool states near the equilibrium state, the exchange rate is close to the market exchange rate. Taking the assumption from before that the pool state is always near the equilibrium, and making one more assumption that most single swaps are not large enough to significantly move the pool state along the constant product curve (this is plausible given that pools have enough liquidity and that swapping huge amounts would result in a bad exchange rate), most swaps will occur near the market rate.

Letting go of assumptions


# Letting go of assumptions

TODO
