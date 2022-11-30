import numpy as np
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

    return stat_dict

def price_impact(output: List[List[OutputTx]], crash_types: List[str]
) -> Tuple[List[Tuple[float, float]], Dict[str, float], List[Tuple[float, float]], Dict[str, float]]:
    """
    Measures magnitude of price impact for transaction pairs before and after 
    transactions' execution as function of proportion of output token balance 
    removed.

    Lower magnitudes are better since they indicate a greater ability to handle
    large volume swaps. It's also expected that as proportionately more of the
    output token balance is drained, the magnitude is higher.

    Parameters:
    1. output: swap metrics
    2. crash_types: what token types crashed in price (are excluded from metrics)

    Returns:
    1. magnitude of percentage changes of exchange rates after each swap
    2. statistics of results
    3. magnitude of percentage changes of exchange rates after each swap with outliers
    removed
    4. statistics of results with outliers removed
    """
    result = []
    
    for lst in output:
        for info in lst:
            if info.outpool_after_val < info.outpool_init_val and \
                 not info.in_type in crash_types and info.after_rate >= 0:
                try:
                    rate = (info.inpool_after_val - info.inpool_init_val) / \
                        (info.outpool_init_val - info.outpool_after_val)
                    drained = 1 - info.outpool_after_val / info.outpool_init_val
                    result.append([drained, abs((info.after_rate - rate) / rate)])
                except:
                    continue
    
    processed_result = remove_outliers(result, OUTLIER_PERC)
    return result, get_stats(result), processed_result, get_stats(processed_result)

def capital_efficiency(output: List[List[OutputTx]], crash_types: List[str]
) -> Tuple[List[Tuple[float, float]], Dict[str, float], List[Tuple[float, float]], Dict[str, float]]:
    """
    Measures deviation from market swap rate as function of proportion of output
    token balance removed

    The ratio internal swap rate / market rate should desireably be near 1 and
    be as low as possible. It's also expected that as proportionately more of
    the output token balance is drained, the ratio is higher.
    
    Parameters:
    1. output: swap metrics
    2. crash_types: what token types crashed in price (are excluded from metrics)

    Returns:
    1. ratios of internal vs market exchange rate for each swap
    2. statistics of results
    3. ratios of internal vs market exchange rate for each swap with outliers removed
    4. statistics of results with outliers removed
    """
    result = []

    for batch in output:
        for info in batch:
            if info.outpool_after_val < info.outpool_init_val and \
                 not info.in_type in crash_types:
                try:
                    rate = (info.inpool_after_val - info.inpool_init_val) / \
                        (info.outpool_init_val - info.outpool_after_val)
                    drained = 1 - info.outpool_after_val / info.outpool_init_val
                    result.append([drained, abs(1 - rate / info.market_rate)])
                except:
                    continue
    
    processed_result = remove_outliers(result, OUTLIER_PERC)
    return result, get_stats(result), processed_result, get_stats(processed_result)

def impermanent_loss(initial: PoolStatusInterface, history: List[List[PoolStatusInterface]],
crash_types: List[str]) -> Tuple[List[float], List[float], Dict[str, float], Dict[str, float],\
    List[float], List[float], Dict[str, float], Dict[str, float]]:
    """
    Measures the amount of impermanent loss or gain between batches

    Parameters:
    1. initial: pool state before any swaps
    2. history: pool state after each transaction
    3. crash_types: what token types crashed in price (are excluded from metrics)

    Returns:
    1. percentage increases of token balances after each swap (relative to start)
    2. percentage decreases of token balances after each swap (relative to start)
    3. statistics on token balance increases
    4. statistics on token balance decreases
    5. percentage increases of token balances after each swap (relative to start)
    with outliers removed
    6. percentage decreases of token balances after each swap (relative to start)
    with outliers removed
    7. statistics on token balance increases with outliers removed
    8. statistics on token balance decreases with outliers removed
    """
    pos_results = []
    neg_results = []
    swap_counter = 1

    for batch in history:
        for status in batch:
            for token in initial:
                if not token in crash_types:
                    change = status[token][0] / initial[token][0] - 1
                    if change > 0:
                        pos_results.append((swap_counter, abs(change)))
                    else:
                        neg_results.append((swap_counter, abs(change)))            
            
            swap_counter += 1
    
    processed_pos_results = remove_outliers(pos_results, OUTLIER_PERC)
    processed_neg_results = remove_outliers(neg_results, OUTLIER_PERC)
    
    return pos_results, neg_results, get_stats(pos_results), get_stats(neg_results), \
    processed_pos_results, processed_neg_results, get_stats(processed_pos_results), get_stats(processed_neg_results)