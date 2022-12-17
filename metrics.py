import numpy as np
import statistics
from typing import List, Tuple, Dict
from outputtx import OutputTx
from poolstatus import PoolStatusInterface

OUTLIER_PERC = 0.0005

def remove_outliers(data: List[Tuple[float, float]], outlier_percent: float
) -> List[Tuple[float, float]]:
    """
    Finds and removes outlier measurements

    Parameters:
    1. data: input data
    2. outlier_percent: percent of measurements that should be outliers

    Returns:
    1. data with outlier measurements removed
    """
    if len(data) > 2:
        data = sorted(data, key = lambda x: x[1])
        sorted_data = [i[1] for i in data]
        med, _ = find_median(sorted_data)
        data = sorted(data, key = lambda x: abs(x[1]-med), reverse=True)
    return data[int(len(data) * outlier_percent):]

def find_median(data: List[float]) -> Tuple[float, List[int]]:
    """
    Computes the indice(s) of or surrounding the median and returns the median

    Parameters:
    1. data: sorted list of values

    Returns:
    1. median value
    2. indice(s) surrounding the median in the input
    """
    indices = []
    list_size = len(data)

    if list_size % 2 == 0:
        indices.append(int(list_size / 2) - 1)
        indices.append(int(list_size / 2))
        median = (data[indices[0]] + data[indices[1]]) / 2
    else:
        indices.append(int(list_size / 2))
        median = data[indices[0]]

    return median, indices

def get_stats(data: List[float]) -> Dict[str, float]:
    """
    Computes and prints statistics given data

    Parameters:
    1. data: data

    Returns:
    1. statistics on Data
    """
    stat_dict = {}
    if len(data) > 2:
        data = sorted(data, key = lambda x: x[1])
        sorted_data = [i[1] for i in data]
        med, median_indices = find_median(sorted_data)
        q1, _ = find_median(sorted_data[:median_indices[0]])
        q3, _ = find_median(sorted_data[median_indices[-1] + 1:])

        stat_dict["avg"], stat_dict["med"] = sum(sorted_data) / len(sorted_data), med
        stat_dict["quart_1"],  stat_dict["quart_3"] = q1, q3
        stat_dict["min"], stat_dict["max"] = sorted_data[0], sorted_data[-1]
        stat_dict["stdv"] = np.std(sorted_data)
        stat_dict["counts"] = len(data)

    return stat_dict

def __match_monitor(output: OutputTx, monitors: set[str]) -> str:
    """
    Returns 'True' if the OutputTx should be monitored

    Parameters:
    1. output: OutputTx to gauge
    2. monitors: tokens or pools to monitor

    Returns
    1. pool or token if output should be monitored
    """
    for test in monitors:
        break
    tok1, tok2 = output.in_type, output.out_type
    if "," in test:
        if tok1 <= tok2:
            val = tok1 + ", " + tok2
            if val in monitors:
                return val
        else:
            val = tok2 + ", " + tok1
            if val in monitors:
                return val
    
    if tok1 in monitors:
        return tok1
    if tok2 in monitors:
        return tok2

    return None

def price_impact(output: List[List[OutputTx]], crash_types: List[str], monitors: set[str]
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]],
    List[Tuple[float, float]], List[Tuple[float, float]], 
    Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float], Dict]:
    """
    Measures price impact for transaction pairs before and after transactions' 
    execution as function of proportion of output token balance removed. Computes
    <swap rate after transaction> / <transaction swap rate>.

    Parameters:
    1. output: swap metrics
    2. crash_types: what token types crashed in price (are excluded from metrics)
    3. monitors: tokens or pools to monitor

    Returns:
    1. rate ratios for every swap, when ratios > 1
    2. rate ratios for every swap, when ratios <= 1
    3. rate ratios for every swap, when ratios > 1, outliers removed
    4. rate ratios for every swap, when ratios <= 1, outliers removed
    5. statistics of swaps when rate ratios > 1
    6. statistics of swaps when rate ratios <= 1
    7. statistics of swaps when rate ratios > 1, outliers removed
    8. statistics of swaps when rate ratios <= 1, outliers removed
    9. statistics and rate ratios for tokens or pools to be monitored
    """
    pos_results = []
    neg_results = []
    monitor_results = {i : [[],[],[],[]] for i in monitors}
    
    for lst in output:
        for info in lst:
            try: 
                rate = (info.inpool_after_val - info.inpool_init_val) / \
                        (info.outpool_init_val - info.outpool_after_val)
                drained = 1 - info.outpool_after_val / info.outpool_init_val
                rate = info.after_rate / rate
                result = [drained, abs(rate)]

                if info.outpool_after_val < info.outpool_init_val and \
                    not info.in_type in crash_types and info.after_rate >= 0:
                    if rate > 1:
                        pos_results.append(result)
                    else:
                        neg_results.append(result)
                
                    monitor = __match_monitor(info, monitors)
                    if monitor != None:
                        if rate > 1:
                            monitor_results[monitor][0].append(result)
                        else:
                            monitor_results[monitor][1].append(result)
            except ZeroDivisionError:
                continue

    proc_pos = remove_outliers(pos_results, OUTLIER_PERC)
    proc_neg = remove_outliers(neg_results, OUTLIER_PERC)

    for v in monitor_results.values():
        pos, neg = v[0], v[1]
        v[2], v[3] = remove_outliers(pos, OUTLIER_PERC), remove_outliers(neg, OUTLIER_PERC)
        v.append(get_stats(pos))
        v.append(get_stats(neg))
        v.append(get_stats(v[2]))
        v.append(get_stats(v[3]))
    
    return pos_results, neg_results, proc_pos, proc_neg, \
    get_stats(pos_results), get_stats(neg_results), get_stats(proc_pos), get_stats(proc_neg), \
    monitor_results

def capital_efficiency(output: List[List[OutputTx]], crash_types: List[str], monitors: set[str]
) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]],
    List[Tuple[float, float]], List[Tuple[float, float]], 
    Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float], Dict]:
    """
    Measures deviation from market swap rate as function of proportion of output
    token balance removed. Computes <internal exchange rage> / <market rate>.
    
    Parameters:
    1. output: swap metrics
    2. crash_types: what token types crashed in price (are excluded from metrics)
    3. monitors: tokens or pools to monitor

    Returns:
    1. rate ratios for every swap, when ratios <= 1
    2. rate ratios for every swap, when ratios > 1
    3. rate ratios for every swap, when ratios <= 1, outliers removed
    4. rate ratios for every swap, when ratios > 1, outliers removed
    5. statistics of swaps when rate ratios <= 1
    6. statistics of swaps when rate ratios > 1
    7. statistics of swaps when rate ratios <= 1, outliers removed
    8. statistics of swaps when rate ratios > 1, outliers removed
    9. statistics and rate ratios for tokens or pools to be monitored
    """
    pos_results = []
    neg_results = []
    monitor_results = {i : [[],[],[],[]] for i in monitors}

    for batch in output:
        for info in batch:
            try:
                rate = (info.inpool_after_val - info.inpool_init_val) / \
                    (info.outpool_init_val - info.outpool_after_val)
                drained = 1 - info.outpool_after_val / info.outpool_init_val
                rate = rate / info.market_rate
                result = ([drained, abs(rate)])

                if info.outpool_after_val < info.outpool_init_val and \
                    not info.in_type in crash_types:
                    if rate <= 1:
                        pos_results.append(result)
                    else:
                        neg_results.append(result)

                monitor = __match_monitor(info, monitors)
                if monitor != None:
                    if rate <= 1:
                        monitor_results[monitor][0].append(result)
                    else:
                        monitor_results[monitor][1].append(result)
            except ZeroDivisionError:
                continue
    
    proc_pos = remove_outliers(pos_results, OUTLIER_PERC)
    proc_neg = remove_outliers(neg_results, OUTLIER_PERC)

    for v in monitor_results.values():
        pos, neg = v[0], v[1]
        v[2], v[3] = remove_outliers(pos, OUTLIER_PERC), remove_outliers(neg, OUTLIER_PERC)
        v.append(get_stats(pos))
        v.append(get_stats(neg))
        v.append(get_stats(v[2]))
        v.append(get_stats(v[3]))

    return pos_results, neg_results, proc_pos, proc_neg, \
    get_stats(pos_results), get_stats(neg_results), get_stats(proc_pos), get_stats(proc_neg), \
    monitor_results

def impermanent_loss(initial: PoolStatusInterface, history: List[List[PoolStatusInterface]],
crash_types: List[str], monitors: set[str]) -> Tuple[
    List[Tuple[int, float]], List[Tuple[int, float]], List[Tuple[int, float]], List[Tuple[int, float]],
    List[Tuple[int, float]], List[Tuple[int, float]], List[Tuple[int, float]], List[Tuple[int, float]],
    Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float],
    Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float],
    Dict]:
    """
    Measures the amount of impermanent loss or gain with respect to the start. Computes
    <current token balance> / <starting token balance>.

    Parameters:
    1. initial: pool state before any swaps
    2. history: pool state after each transaction
    3. crash_types: what token types crashed in price (are excluded from metrics)
    4. monitors: tokens or pools to monitor

    Returns:
    1. balance ratios after every swap, when ratios >= 1
    2. balance ratios after every swap, when ratios < 1
    3. average balance ratios across all tokens after each swap
    4. median balance ratio across all tokens after each swap
    5. balance ratios after every swap, when ratios >= 1, outliers removed
    6. balance ratios after every swap, when ratios < 1, outliers removed
    7. average balance ratios across all tokens after each swap, outliers removed
    8. median balance ratio across all tokens after each swap, outliers removed
    9. statistics on balance ratios, when ratios >= 1
    10. statistics on balance ratios, when ratios < 1
    11. statistics on average balance ratios
    12. statistics on median balance ratios
    13. statistics on balance ratios, when ratios >= 1, outliers removed
    14 statistics on balance ratios, when ratios < 1, outliers removed
    15. statistics on average balance ratios, outliers removed
    16. statistics on median balance ratios, outliers removed
    17. statistics and ratios for tokens or pools to be monitored
    """
    pos_results = []
    neg_results = []
    averages = []
    medians = []
    monitor_results = {i : [[],[],[],[]] for i in monitors}
    swap_counter = 1

    for batch in history:
        for status in batch:
            no_crash_hits = 0
            avg = 0
            changes = []
            for token in initial:
                change = status[token][0] / initial[token][0]
                if not token in crash_types:
                    changes.append(change)
                    avg += change
                    no_crash_hits += 1
                    if change >= 1:
                        pos_results.append((swap_counter, abs(change)))
                    else:
                        neg_results.append((swap_counter, abs(change)))
                
                pool = ""
                if isinstance(token, Tuple):
                    tok1, tok2 = token[0], token[1]
                    if tok1 <= tok2:
                        pool = tok1 + ", " + tok2
                    else:
                        pool = tok2 + ", " + tok1
                
                found = None
                if token in monitor_results:
                    found = token
                elif pool in monitor_results:
                    found = pool

                if found != None:
                    if change >= 1:
                        monitor_results[found][0].append((swap_counter, abs(change)))
                    else:
                        monitor_results[found][1].append((swap_counter, abs(change)))           
            
            avg /= no_crash_hits
            medians.append([swap_counter, statistics.median(changes)])
            averages.append([swap_counter, avg])
            
            swap_counter += 1
    
    proc_pos = remove_outliers(pos_results, OUTLIER_PERC)
    proc_neg = remove_outliers(neg_results, OUTLIER_PERC)
    proc_avg = remove_outliers(averages, OUTLIER_PERC)
    proc_med = remove_outliers(medians, OUTLIER_PERC)
    for v in monitor_results.values():
        pos, neg = v[0], v[1]
        v[2], v[3] = remove_outliers(pos, OUTLIER_PERC), remove_outliers(neg, OUTLIER_PERC)
        v.append(get_stats(pos))
        v.append(get_stats(neg))
        v.append(get_stats(v[2]))
        v.append(get_stats(v[3]))
 
    return pos_results, neg_results, averages, medians, \
    proc_pos, proc_neg, proc_avg, proc_med, \
    get_stats(pos_results), get_stats(neg_results), get_stats(averages), get_stats(medians), \
    get_stats(proc_pos), get_stats(proc_neg), get_stats(proc_avg), get_stats(proc_med), monitor_results