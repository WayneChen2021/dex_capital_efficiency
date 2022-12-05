# multi-token-proactive-market-maker

note: This is a continuation of a group project from summer 2022, and I am now working on it by myself

## Running the code

1. Modify the config JSONs. They follow this form:
```json
{
    "initializer": {
        "init_kwargs": {
            "constant": "// approximate pool size",
            "k": "// k parameter for PMM, MPMM if it is not set randomly",
            "cap_limit": "// market cap of any single token",
            "random_k": "// 'True' if k parameters set randomly for PMM, MPMM"
        },
        "token_configs": {
            "token_infos": {
                "traffic_gen": {
                    "// token name, optional entry": {
                        "intype_percent": "// percentage of swaps depositing this token, optional entry",
                        "outtype_percent": "// percentage of swaps removing this token, optional entry"
                    }
                },
                "price_gen": {
                    "// token name": {
                        "start": "// start price",
                        "mean": "// mean % price change, optional entry (default in 'price_gen')",
                        "stdv": "// stdv of price change, optional entry (default in 'price_gen')",
                        "change_probability": "// probability of price change, optional entry (default in 'price_gen')"
                    }
                }
            }
        }
    },
    "traffic": {
        "init_kwargs": {
            "sigma": "// stdv of swap amount (wrt an actual currency)",
            "mean": "// average swap amount (wrt an actual currency)",
            "arb_probability": "// percent of swaps that are purely for arbitrage",
            "shape": "// [num of batches, batch size]; prices change between batches",
            "max_price": "// maximum amount of any swap (wrt an actual currency)",
            "is_norm": "// 'True' if swap amount is normally distributed (else it's uniform from (0, max_price))"
        }
    },
    "price_gen": {
        "init_kwargs": {
            "mean": "// average % of price change",
            "stdv": "// stdv of price change",
            "change_probability": "// probability of price changing",
            "batches": "num of batches; should match with 'shape' in 'traffic'"
        }
    },
    "market_maker": {
        "type": "// market maker type (AMM, CSMM, etc)",
        "simulate_kwargs": {
            "reset_tx": "// 'True' if reset pool states after each batch",
            "arb": "// 'True' if arbitrage should be simulated",
            "arb_actions": "// number of swaps per arbitrage action",
            "multi_token": "// 'True' if market maker has multi token pools (name begins with M)"
        }
    }
}
```

2. ```python simulator.py```

## Analyzing results
