class InputTx:
    def __init__(self, intype : str, outtype : str, inval : float, is_arb : bool = False):
        """
        Represents one transaction to in traffic

        Parameters:
        intype: input token name
        outtype: output token name
        inval: amount of input token to be inserted in market maker's liquidity pool
        is_arb: whether or not this transaction is processed or will result in
        call to arbitrage() in market maker
        """
        self.intype  = intype
        self.outtype = outtype
        self.inval = inval
        self.is_arb = is_arb
