
class OutputTx:
    def __init__(self,
                 in_type: str,
                 out_type: str,
                 inpool_init_val: float,
                 outpool_init_val: float,
                 inpool_after_val: float,
                 outpool_after_val: float,
                 market_rate: float,
                 after_rate: float
                 ):
        """
        Information associated with each swap for computing metrics

        Parameters:
        1. in_type: input token name
        2. out_type: output token name
        3. inpool_init_val: amount of input token originally in market maker's liquidiy pool
        4. outpool_init_val: amount of output token originally in market maker's liquidiy pool
        5. inpool_after_val: amount of input token in market maker's liquidiy pool after swap
        6. outpool_after_val: amount of output token in market maker's liquidiy pool after swap
        7. market_rate: exchange rate in market outside market maker
        8. after_rate: exchange rate inside market maker of swap types after swap occurs
        """
        self.in_type = in_type
        self.out_type = out_type
        self.inpool_init_val = inpool_init_val
        self.outpool_init_val = outpool_init_val
        self.inpool_after_val = inpool_after_val
        self.outpool_after_val = outpool_after_val
        self.market_rate = market_rate
        self.after_rate = after_rate