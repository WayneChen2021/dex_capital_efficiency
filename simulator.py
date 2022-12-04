import json
import pickle
import os
from typing import Tuple, Dict

import marketmakers
import metrics
from initializer import Initializer
from pricegen import PriceGenerator
from trafficgen import TrafficGenerator

import matplotlib.pyplot as plt
import json

def simulate(config: Dict) -> Tuple[str, str]:
    """
    Performs simulation given a market type and market maker

    Parameters:
    1. config: JSON containing configuration

    Returns:
    1. path to generated prices
    2. path to generated traffic
    """
    initializer = Initializer(**config["initializer"]["init_kwargs"])
    initializer.configure_tokens(**config["initializer"]["token_configs"])
    pairwise_pools, pairwise_infos, single_pools, single_infos, \
        traffic_info, price_gen_info, crash_types, cap_limit = initializer.get_stats()

    traffic_generator = TrafficGenerator(**config['traffic']['init_kwargs'])
    traffic_generator.configure_tokens(single_pools, traffic_info, cap_limit)

    price_generator = PriceGenerator(**config['price_gen']['init_kwargs'])
    price_generator.configure_tokens(price_gen_info)

    MMClass = getattr(marketmakers, config['market_maker']['type'])
    mm = MMClass(pairwise_pools, pairwise_infos, single_pools, single_infos,)
    mm.configure_simulation(**config['market_maker']['simulate_kwargs'])
    mm.configure_crash_types(crash_types)

    # generate prices, traffic and store in files
    price_dir = os.path.join(run_dir, market + "_price.obj")
    if not os.path.exists(price_dir):
        ext_prices = price_generator.simulate_ext_prices()
        f = open(price_dir, "wb")
        pickle.dump(ext_prices, f)
        f.close()
    else:
        f = open(price_dir, "rb")
        ext_prices = pickle.load(f)
        f.close()
    
    traffic_dir = os.path.join(run_dir, market + "_traffic.obj")
    if not os.path.exists(traffic_dir):
        traffics = traffic_generator.generate_traffic(ext_prices)
        f = open(traffic_dir, "wb")
        pickle.dump(traffics, f)
        f.close()
    else:
        f = open(traffic_dir, "rb")
        traffics = pickle.load(f)
        f.close()

    outputs, statuses, status0, crash_types = mm.simulate_traffic(traffics, ext_prices)

    # compute metrics
    cap_eff, cap_eff_dict, proc_cap_eff, proc_cap_eff_dict = metrics.capital_efficiency(outputs, crash_types)
    imp_gain, imp_loss, gain_dict, loss_dict, proc_imp_gain, proc_imp_loss, proc_gain_dict, proc_loss_dict =\
         metrics.impermanent_loss(status0, statuses, crash_types)
    price_imp, price_imp_dict, proc_price_imp, proc_price_imp_dict = metrics.price_impact(outputs, crash_types)
    all_info_dict = {
        "cap_eff": cap_eff_dict,
        "imp_gain": gain_dict,
        "imp_loss": loss_dict,
        "price_imp": price_imp_dict,
        "proc_cap_eff": proc_cap_eff_dict,
        "proc_imp_gain": proc_gain_dict,
        "proc_imp_loss": proc_loss_dict,
        "proc_price_imp": proc_price_imp_dict
    }
    all_info_str = json.dumps(all_info_dict, indent=4)
    print("data for {n} on {m}:".format(n=mm_name, m=market))
    print(all_info_str)

    # write stats
    with open("{d}/stats/{m}/{n}.json".format(d=run_dir, m=market, n=mm_name), "w") as f:
        f.write(all_info_str)
    
    if save_images:
        # price_impact
        plt.scatter([x[0] for x in price_imp], [x[1] for x in price_imp], s=1)
        plt.savefig('{d}/images/{m}/price_imp/{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()
        plt.scatter([x[0] for x in proc_price_imp], [x[1] for x in proc_price_imp], s=1)
        plt.savefig('{d}/images/{m}/price_imp/proc_{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()
        
        # capital efficiency
        plt.scatter([x[0] for x in cap_eff], [x[1] for x in cap_eff], s=1)
        plt.savefig('{d}/images/{m}/cap_eff/{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()
        plt.scatter([x[0] for x in proc_cap_eff], [x[1] for x in proc_cap_eff], s=1)
        plt.savefig('{d}/images/{m}/cap_eff/proc_{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()
        
        # impermanent loss
        plt.scatter([x[0] for x in imp_gain], [x[1] for x in imp_gain], s=1)
        plt.savefig('{d}/images/{m}/imp_gain/{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()
        plt.scatter([x[0] for x in proc_imp_gain], [x[1] for x in proc_imp_gain], s=1)
        plt.savefig('{d}/images/{m}/imp_gain/proc_{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()
        plt.scatter([x[0] for x in imp_loss], [x[1] for x in imp_loss], s=1)
        plt.savefig('{d}/images/{m}/imp_loss/{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()
        plt.scatter([x[0] for x in proc_imp_loss], [x[1] for x in proc_imp_loss], s=1)
        plt.savefig('{d}/images/{m}/imp_loss/proc_{n}.png'.format(d=run_dir, m=market, n=mm_name))
        plt.clf()

    if save_data:
        # price_impact
        pickle.dump(price_imp, \
            open("{d}/raw_data/{m}/price_imp/{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
        pickle.dump(proc_price_imp, \
            open("{d}/raw_data/{m}/price_imp/proc_{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
        
        # capital efficiency
        pickle.dump(cap_eff, \
            open("{d}/raw_data/{m}/cap_eff/{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
        pickle.dump(proc_cap_eff, \
            open("{d}/raw_data/{m}/cap_eff/proc_{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
        
        # impermanent loss
        pickle.dump(imp_gain, \
            open("{d}/raw_data/{m}/imp_gain/{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
        pickle.dump(proc_imp_gain, \
            open("{d}/raw_data/{m}/imp_gain/proc_{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
        pickle.dump(imp_loss, \
            open("{d}/raw_data/{m}/imp_loss/{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
        pickle.dump(proc_imp_loss, \
            open("{d}/raw_data/{m}/imp_loss/proc_{n}.pkl".format(d=run_dir, m=market, n=mm_name), "wb"))
    
    return price_dir, traffic_dir

if __name__ == '__main__':
    runs = input("number of simulation runs: ")
    base_dir = input("output file directory: ")
    save_images = input("store images? (Y/N): ") == "Y"
    save_data = input("store raw data? (Y/N): ") == "Y"
    save_generated = input("save generated price and traffic objects? (Y/N): ") == "Y"

    pretty_metric = {
        "cap_eff": "capital efficiency",
        "imp_gain": "impermanent gain",
        "imp_loss": "impermanent loss",
        "price_imp": "price impact",
        "proc_cap_eff": "capital efficiency",
        "proc_imp_gain": "impermanent gain",
        "proc_imp_loss": "impermanent loss",
        "proc_price_imp": "price impact"
    }

    pretty_xlabel = {
        "cap_eff": "deviation from market rate",
        "imp_gain": "percentage gain",
        "imp_loss": "percentage loss",
        "price_imp": "percentage change in exchange rate",
        "proc_cap_eff": "deviation from market rate",
        "proc_imp_gain": "percentage gain",
        "proc_imp_loss": "percentage loss",
        "proc_price_imp": "percentage change in exchange rate"
    }

    pretty_market = {
        "double_price_crash": "two token crash",
        "single_price_crash": "single token crash",
        "random": "regular market",
        "volatile_price": "volatile market"
    }

    data_formats = ["images", "stats", "raw_data"]
    metric_types = ["price_imp", "cap_eff", "imp_gain", "imp_loss"]
    full_metric_types = metric_types + ["proc_" + i for i in metric_types]

    if not os.path.exists(base_dir):
        os.mkdir(base_dir)
    
    for i in range(int(runs)):
        run_dir = os.path.join(base_dir, "run_" + str(i))
        if not os.path.exists(run_dir):
            os.mkdir(run_dir)

        stat_dir_dict = {}
        for dir in data_formats:
            if (dir == "stats") or (dir == "images" and save_images) or (dir == "raw_data" and save_data):
                combined_dir = os.path.join(run_dir, dir)
                if not os.path.exists(combined_dir):
                    os.mkdir(combined_dir)
                
                if dir != "stats":
                    for market in os.listdir("config"):
                        market_dir = os.path.join(combined_dir, market)
                        if not os.path.exists(market_dir):
                            os.mkdir(market_dir)

                        for stat in metric_types:
                            stat_dir = os.path.join(market_dir, stat)
                            if not os.path.exists(stat_dir):
                                os.mkdir(stat_dir)
                else:
                    for market in os.listdir("config"):
                        market_dir = os.path.join(combined_dir, market)
                        if not os.path.exists(market_dir):
                            stat_dir_dict[market] = market_dir
                            os.mkdir(market_dir)         
        
        for market in os.listdir("config"):
            market_path = os.path.join("config", market)
            price_dir, traffic_dir = None, None

            for env in os.listdir(market_path):
                mm_name = env[:-5]
                with open(os.path.join(market_path, env), 'r') as f:
                    config = json.load(f)

                price_dir, traffic_dir = simulate(config)
            
            if not save_generated:
                os.remove(price_dir)
                os.remove(traffic_dir)

        if save_images:
            for market in stat_dir_dict:
                for metric in full_metric_types:
                    boxes = []
                    stats_dir = stat_dir_dict[market]
                    for mm in os.listdir(stats_dir):
                        with open(os.path.join(stats_dir, mm), "r") as f:
                            all_info = json.loads(f.read())
                        
                        if len(all_info) and metric in all_info:
                            info = all_info[metric]
                            if len(info):
                                if not("c" in mm and ("cap" in metric or "price" in metric)):
                                    boxes.append({
                                        'label' : mm[:-5].replace("_0", ", k=0."),
                                        'whislo': info["quart_1"],
                                        'q1'    : info["quart_1"],
                                        'med'   : info["med"],
                                        'q3'    : info["quart_3"],
                                        'whishi': info["max"],
                                        'fliers': [] 
                                    })
                    
                    data_type = "raw"
                    if "proc" in metric:
                        data_type = "processed"
                    save_dir = "{}/run_{}/images/{}/{}/aggregated_{}.png".format(
                        base_dir, i, market, metric.replace("proc_", ""), metric)

                    _, ax = plt.subplots()
                    ax.bxp(boxes, vert=False, showfliers=False, patch_artist=True)
                    ax.set_title("run {}, {}: {} {}".format(i, pretty_market[market], data_type, pretty_metric[metric]))
                    ax.set_xlabel(pretty_xlabel[stat])
                    ax.set_ylabel("market makers")
                    ax.set_xscale("log")
                    plt.tight_layout()
                    plt.savefig(save_dir)
                    plt.close()
