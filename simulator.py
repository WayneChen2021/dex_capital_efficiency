import json
import pickle
import os
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import json
import pandas as pd
from typing import Tuple, Dict, List
from copy import deepcopy
from collections import OrderedDict
from argparse import ArgumentParser
from datetime import datetime

import marketmakers
import metrics
from initializer import Initializer
from pricegen import PriceGenerator
from trafficgen import TrafficGenerator
from inputtx import InputTx

labels = {
    "cap_eff": ["% pool drained", "internal, external rate ratio"],
    "imp": ["swap number", "% token balance remaining"],
    "price_imp": ["% pool drained", "internal, external rate ratio"]
}

pretty_market = {
    "large_crash": "expensive token crash",
    "stable_crash": "stablecoin crash",
    "random": "regular market",
    "volatile_price": "volatile market"
}

stat_groups = {
    "cap_eff": ["better", "worse"],
    "price_imp": ["increase", "decrease"],
    "imp": ["gain", "loss", "averages", "median"]
}

data_formats = ["images", "stats", "raw_data"]
metric_types = ["price_imp", "cap_eff", "imp"]

def initialize_simulation(config: Dict, load_true_data: bool = False, load_true_txs: bool = False) -> Tuple[List[Tuple[str, str]], List[Tuple[float, float, float]],
    List[str], List[Tuple[float, float]],
    Dict[str, Dict[str, float]], Dict[str, Dict[str, float]],
    List[str], float,
    List[str], List[Tuple[str]],
    List[List[InputTx]], List[Dict[str, float]],
    str, str]:
    """
    Initializes prices, traffic, and other information for swap simulation

    Parameters:
    1. config: JSON containing configuration

    Returns:
    1. list of pairwise token pools
    2. balance and k values for pairwise token pools
    3. list of tokens
    4. balance and k values for single tokens
    5. token information for traffic generator
    6. token information for price generator
    7. token types that are crashing
    8. maximum token market cap
    9. batches of InputTx for simulation
    10. prices of tokens for every batch
    11. address to price object
    12. address of traffic object
    """
    initializer = Initializer(**config["initializer"]["init_kwargs"])
    initializer.configure_tokens(**config["initializer"]["token_configs"])
    pairwise_pools, pairwise_infos, single_pools, single_infos, traffic_info, price_gen_info, \
    crash_types, cap_limit = initializer.get_stats()

    traffic_generator = TrafficGenerator(**config['traffic']['init_kwargs'])
    traffic_generator.configure_tokens(single_pools, traffic_info, cap_limit)

    # generate prices, traffic and store in files
    price_dir = os.path.join(run_dir, market + "_price.obj")
    if not load_true_data:
        price_generator = PriceGenerator(**config['price_gen']['init_kwargs'])
        price_generator.configure_tokens(price_gen_info)

        ext_prices = price_generator.simulate_ext_prices()
    else:
        timestamps_to_info = OrderedDict()
        coins_df = pd.read_csv('true_data/coins.csv')
        ids_to_symbols = {int(row['id']) : row['Symbol'] for _, row in coins_df.iterrows()}

        for csv_path in os.listdir('true_data/hourly_prices'):
            symbol = ids_to_symbols[int(csv_path[: csv_path.index('_')])]
            coin_df = pd.read_csv(f'true_data/hourly_prices/{csv_path}')
            
            for _, row in coin_df.iterrows():
                timestamp = f"{row['Date']} {row['Time']}"
                if not timestamp in timestamps_to_info:
                    timestamps_to_info[timestamp] = {symbol: float(row['Open'])}
                else:
                    timestamps_to_info[timestamp][symbol] = float(row['Open'])
        
        ext_prices: List[Tuple[datetime, Dict[str, float]]] = [(datetime.strptime(dt, '%Y-%m-%d %H:%M:%S'), infos) for dt, infos in timestamps_to_info.items()]

    f = open(price_dir, "wb")
    pickle.dump(list(timestamps_to_info.values()), f)
    f.close()         
    
    traffic_dir = os.path.join(run_dir, market + "_traffic.obj")
    traffics = traffic_generator.generate_traffic(ext_prices, load_true_txs)
    f = open(traffic_dir, "wb")
    pickle.dump(traffics, f)
    f.close()
    
    return pairwise_pools, pairwise_infos, single_pools, single_infos, traffic_info, price_gen_info, \
    crash_types, cap_limit, list(timestamps_to_info.values()), traffics, price_dir, traffic_dir

def __pack_data(stat: str, raw: List, processed: List, monitors: Dict) -> Dict:
    """
    Packs data into a dictionary for processing later

    Parameters:
    1. stat: name of state (i.e. 'cap_eff')
    2. raw: list of raw data arrays
    3. processed: list of processed data arrays, with corresponding indices in raw
    4. monitors: tokens or pools monitored

    Returns:
    1. dictionary mapping all information
    """
    dictionary =  {
        stat_groups[stat][i] : {"raw": raw[i], "processed": processed[i]} for i in range(len(raw))
    }
    try:
        dictionary["m"] = {
            i : {"raw": raw[i], "processed": processed[i]} for i in monitors
        }
    except Exception as e:
        import pdb; pdb.set_trace()
    return dictionary

def simulate(config: Dict, 
    pairwise_pools: List[Tuple[str, str]], pairwise_infos: List[Tuple[float, float, float]],
    single_pools: List[str], single_infos: List[Tuple[float, float]],
    crash_types: List[str],
    traffics: List[List[InputTx]], ext_prices: List[Dict[str, float]]
    ) -> None:
    """
    Performs simulation given a market type and market maker

    Parameters:
    1. config: JSON containing configuration
    2. pairwise_pools: list of pairwise token pools
    3. pairwise_infos: balance and k values for pairwise token pools
    4. single_pools: list of tokens
    5. single_infos: balance and k values for single tokens
    6. crash_types: token types that are crashing
    7. traffics: batches of InputTx for simulation
    8. ext_prices: prices of tokens for every batch
    9. multi_monitors: tokens to monitor in multi-token setting
    10. pairwise_monitors: pools to monitor in pairwise-pool setting

    Returns:
    1. path to generated prices
    2. path to generated traffic
    """
    MMClass = getattr(marketmakers, config['type'])
    mm = MMClass(pairwise_pools, pairwise_infos, single_pools, single_infos)
    mm.configure_simulation(**config['simulate_kwargs'])
    mm.configure_crash_types(crash_types)

    outputs, statuses, status0, crash_types = mm.simulate_traffic(traffics, ext_prices)
    monitor = set()
    if config['simulate_kwargs']['multi_token'] == "True":
        for tok in config['simulate_kwargs']['multi_monitors']:
            monitor.add(tok)
    else:
        for tup in config['simulate_kwargs']['pairwise_monitors']:
            tok1, tok2 = tup[0], tup[1]
            if tok1 <= tok2:
                monitor.add(tok1 + ", " + tok2)
            else:
                monitor.add(tok2 + ", " + tok1)

    # compute metrics
    pos_cap, neg_cap, proc_pos_cap, proc_neg_cap, \
    pos_cap_dict, neg_cap_dict, proc_pos_cap_dict, proc_neg_cap_dict, \
    cap_monitor = metrics.capital_efficiency(outputs, crash_types, monitor)
    cap_eff_dict = {
        stat_groups["cap_eff"][0]: {
            "raw": pos_cap_dict,
            "processed": proc_pos_cap_dict
        },
        stat_groups["cap_eff"][1]: {
            "raw": neg_cap_dict,
            "processed": proc_neg_cap_dict
        },
        "monitors": {
            i : {
                stat_groups["cap_eff"][0]: {
                    "raw": cap_monitor[i][4],
                    "processed": cap_monitor[i][6]
                },
                stat_groups["cap_eff"][1]: {
                    "raw": cap_monitor[i][5],
                    "processed": cap_monitor[i][7]
                }
            } for i in cap_monitor
        }
    }

    pos_pri, neg_pri, proc_pos_pri, proc_neg_pri, \
    pos_pri_dict, neg_pri_dict, proc_pos_pri_dict, proc_neg_pri_dict, \
    pri_monitor = metrics.price_impact(outputs, crash_types, monitor)
    pri_dict = {
        stat_groups["price_imp"][0]: {
            "raw": pos_pri_dict,
            "processed": proc_pos_pri_dict
        },
        stat_groups["price_imp"][1]: {
            "raw": neg_pri_dict,
            "processed": proc_neg_pri_dict
        },
        "monitors": {
            i : {
                stat_groups["price_imp"][0]: {
                    "raw": pri_monitor[i][4],
                    "processed": pri_monitor[i][6]
                },
                stat_groups["price_imp"][1]: {
                    "raw": pri_monitor[i][5],
                    "processed": pri_monitor[i][7]
                }
            } for i in pri_monitor
        }
    }

    imp_gain, imp_loss, imp_avg, imp_med, \
    proc_imp_gain, proc_imp_loss, proc_imp_avg, proc_imp_med, \
    imp_gain_dict, imp_loss_dict, imp_avg_dict, imp_med_dict, \
    proc_imp_gain_dict, proc_imp_loss_dict, proc_imp_avg_dict, proc_imp_med_dict, \
    imp_monitor = metrics.impermanent_loss(status0, statuses, crash_types, monitor)
    imp_dict = {
        stat_groups["imp"][0]: {
            "raw": imp_gain_dict,
            "processed": proc_imp_gain_dict
        },
        stat_groups["imp"][1]: {
            "raw": imp_loss_dict,
            "processed": proc_imp_loss_dict
        },
        stat_groups["imp"][2]: {
            "raw": imp_avg_dict,
            "processed": proc_imp_avg_dict
        },
        stat_groups["imp"][3]: {
            "raw": imp_med_dict,
            "processed": proc_imp_med_dict
        },
        "monitors": {
            i : {
                stat_groups["imp"][0]: {
                    "raw": imp_monitor[i][4],
                    "processed": imp_monitor[i][6]
                },
                stat_groups["imp"][1]: {
                    "raw": imp_monitor[i][5],
                    "processed": imp_monitor[i][7]
                }
            } for i in imp_monitor
        }
    }

    all_info_dict = {
        "capital efficiency": cap_eff_dict,
        "impermanent gain, loss": imp_dict,
        "price impact": pri_dict
    }
    all_info_str = json.dumps(all_info_dict, indent=4)
    market_name, pretty_mm_name = pretty_market[market], mm_name.replace("_0", " k=0.")

    # write stats
    with open("{}/stats/{}/{}.json".format(run_dir, market, mm_name), "w") as f:
        f.write(all_info_str)
    
    if save_images:
        # price_impact
        combined = pos_pri + neg_pri
        plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label="all tokens")
        for i in pri_monitor:
            combined = pri_monitor[i][0] + pri_monitor[i][1]
            plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label=i)
        plt.title("run {}, {} price impact: {}".format(run_count, market_name, pretty_mm_name))
        plt.xlabel(labels["price_imp"][0])
        plt.ylabel(labels["price_imp"][1])
        plt.yscale("log")
        plt.legend(loc='best')
        plt.tight_layout()
        plt.savefig('{}/images/{}/price_imp/{}.png'.format(run_dir, market, mm_name), bbox_inches='tight')
        plt.clf()
        
        combined = proc_pos_pri + proc_neg_pri
        plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label="all tokens")
        for i in pri_monitor:
            combined = pri_monitor[i][2] + pri_monitor[i][3]
            plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label=i)
        plt.title("run {}, {} processed price impact: {}".format(run_count, market_name, pretty_mm_name))
        plt.xlabel(labels["price_imp"][0])
        plt.ylabel(labels["price_imp"][1])
        plt.yscale("log")
        plt.legend(loc='best')
        plt.tight_layout()
        plt.savefig('{}/images/{}/price_imp/proc_{}.png'.format(run_dir, market, mm_name), bbox_inches='tight')
        plt.clf()
        
        # capital efficiency
        combined = pos_cap + neg_cap
        plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label="all tokens")
        for i in cap_monitor:
            combined = cap_monitor[i][0] + cap_monitor[i][1]
            plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label=i)
        plt.title("run {}, {} capital efficiency: {}".format(run_count, market_name, pretty_mm_name))
        plt.xlabel(labels["cap_eff"][0])
        plt.ylabel(labels["cap_eff"][1])
        plt.yscale("log")
        plt.legend(loc='best')
        plt.tight_layout()
        plt.savefig('{}/images/{}/cap_eff/{}.png'.format(run_dir, market, mm_name), bbox_inches='tight')
        plt.clf()
        
        combined = proc_pos_cap + proc_neg_cap
        plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label="all tokens")
        for i in cap_monitor:
            combined = cap_monitor[i][2] + cap_monitor[i][3]
            plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label=i)
        plt.title("run {}, {} processed capital efficiency: {}".format(run_count, market_name, pretty_mm_name))
        plt.xlabel(labels["cap_eff"][0])
        plt.ylabel(labels["cap_eff"][1])
        plt.yscale("log")
        plt.legend(loc='best')
        plt.tight_layout()
        plt.savefig('{}/images/{}/cap_eff/proc_{}.png'.format(run_dir, market, mm_name), bbox_inches='tight')
        plt.clf()
        
        # impermanent loss
        combined = imp_gain + imp_loss
        plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label="all tokens")
        plt.scatter([x[0] for x in imp_avg], [x[1] for x in imp_avg], s=1, label="all token averages")
        plt.scatter([x[0] for x in imp_med], [x[1] for x in imp_med], s=1, label="all token median")
        for i in imp_monitor:
            combined = imp_monitor[i][0] + imp_monitor[i][1]
            plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label=i)
        plt.title("run {}, {} impermanent loss, gain: {}".format(run_count, market_name, pretty_mm_name))
        plt.xlabel(labels["imp"][0])
        plt.ylabel(labels["imp"][1])
        plt.yscale("log")
        plt.legend(loc='best')
        plt.tight_layout()
        plt.savefig('{}/images/{}/imp/{}.png'.format(run_dir, market, mm_name), bbox_inches='tight')
        plt.clf()
        
        combined = proc_imp_gain + proc_imp_loss
        plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label="all tokens")
        plt.scatter([x[0] for x in proc_imp_avg], [x[1] for x in proc_imp_avg], s=1, label="all token averages")
        plt.scatter([x[0] for x in proc_imp_med], [x[1] for x in proc_imp_med], s=1, label="all token median")
        for i in imp_monitor:
            combined = imp_monitor[i][2] + imp_monitor[i][3]
            plt.scatter([x[0] for x in combined], [x[1] for x in combined], s=1, label=i)
        plt.title("run {}, {} impermanent loss, gain: {}".format(run_count, market_name, pretty_mm_name))
        plt.xlabel(labels["imp"][0])
        plt.ylabel(labels["imp"][1])
        plt.yscale("log")
        plt.legend(loc='best')
        plt.tight_layout()
        plt.savefig('{}/images/{}/imp/proc_{}.png'.format(run_dir, market, mm_name), bbox_inches='tight')
        plt.clf()

    if save_data:
        cap_eff_data = __pack_data('cap_eff', [pos_cap, neg_cap], [proc_pos_cap, proc_neg_cap], cap_monitor)
        pri_data = __pack_data('price_imp', [pos_pri, neg_pri], [proc_pos_pri_dict, proc_neg_pri_dict], pri_monitor)
        imp_data = __pack_data('imp',
                [imp_gain, imp_loss, imp_avg, imp_med],
                [proc_imp_gain, proc_imp_loss, proc_imp_avg, proc_imp_med],
                imp_monitor)

        # price_impact
        pickle.dump(pri_data, \
            open("{}/raw_data/{}/price_imp/{}.pkl".format(run_dir, market, mm_name), "wb"))
        
        # capital efficiency
        pickle.dump(cap_eff_data, \
            open("{}/raw_data/{}/cap_eff/{}.pkl".format(run_dir, market, mm_name), "wb"))
        
        # impermanent loss
        pickle.dump(imp_data, \
            open("{}/raw_data/{}/imp/{}.pkl".format(run_dir, market, mm_name), "wb"))

def yes_no(query: str) -> bool:
    """
    Runs a query for input that should receive a Y/N for response

    Parameters:
    1. query: query string

    Returns:
    1. whether or not the response was 'Y'
    """
    dict_check = {"Y": True, "N": True}
    while True:
        try:
            output = input(query)
            _ = dict_check[output]
        except KeyError:
            print("Please enter 'Y' or 'N'")
            continue
        else:
            return output == 'Y'

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--configs_path', type=str, required=True)
    parser.add_argument('--existing_prices', action='store_true')
    parser.add_argument('--existing_txs', action='store_true')
    args = parser.parse_args()

    while True:
        try:
            runs = int(input("number of simulation runs: "))
            _ = 1 / max(0, runs)
        except ValueError:
            print("Please enter a valid integer")
            continue
        except ZeroDivisionError:
            print("Please enter a positive integer")
            continue
        else:
            break
    base_dir = input("output file directory: ")
    save_images = yes_no("store images? (Y/N): ")
    save_data = yes_no("store raw data? (Y/N): ")
    save_generated = yes_no("save generated price and traffic objects? (Y/N): ")
    
    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
    
    for run_count in range(int(runs)):
        run_dir = os.path.join(base_dir, "run_" + str(run_count))
        if not os.path.exists(run_dir):
            os.mkdir(run_dir)

        stat_dir_dict = {}
        for dir in data_formats:
            if (dir == "stats") or (dir == "images" and save_images) or (dir == "raw_data" and save_data):
                combined_dir = os.path.join(run_dir, dir)
                if not os.path.exists(combined_dir):
                    os.mkdir(combined_dir)
                
                if dir != "stats":
                    for market in os.listdir(args.configs_path):
                        if not "json" in market:
                            market_dir = os.path.join(combined_dir, market)
                            if not os.path.exists(market_dir):
                                os.mkdir(market_dir)

                            for stat in metric_types:
                                stat_dir = os.path.join(market_dir, stat)
                                if not os.path.exists(stat_dir):
                                    os.mkdir(stat_dir)

                else:
                    for market in os.listdir(args.configs_path):
                        if not "json" in market:
                            market_dir = os.path.join(combined_dir, market)
                            if not os.path.exists(market_dir):
                                stat_dir_dict[market] = market_dir
                                os.mkdir(market_dir)         
        
        for market in os.listdir(args.configs_path):
            if not "json" in market:
                market_path = os.path.join(args.configs_path, market)
                with open(os.path.join(market_path, "init.json"), 'r') as f:
                    config = json.load(f)
                pairwise_pools, pairwise_infos, single_pools, single_infos, traffic_info, \
                price_gen_info, crash_types, cap_limit, ext_prices, traffics, \
                price_dir, traffic_dir = initialize_simulation(config, args.existing_prices, args.existing_txs)
               
                for mm in os.listdir(args.configs_path):
                    if "json" in mm:
                        mm_name = mm[:-5]
                        with open(os.path.join(args.configs_path, mm), 'r') as f:
                            config = json.load(f)

                        simulate(
                            config,
                            deepcopy(pairwise_pools), deepcopy(pairwise_infos),
                            deepcopy(single_pools), deepcopy(single_infos),
                            crash_types,
                            deepcopy(traffics), ext_prices
                        )
            
                if not save_generated:
                    os.remove(price_dir)
                    os.remove(traffic_dir)