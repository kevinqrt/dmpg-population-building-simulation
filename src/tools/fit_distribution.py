# some links
# https://stackoverflow.com/questions/6620471/fitting-empirical-distribution-to-theoretical-ones-with-scipy-python/16651955#16651955
# https://erdogant.github.io/distfit/pages/html/index.html

import math
import random
import warnings
from typing import Any, Tuple, List

import distfit
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from pandas import DataFrame

warnings.filterwarnings("ignore")

NUMBER_OF_DATA_POINTS = 5000
EXCEL_FILE_NAME = 'data.xlsx'


def headline(inline: str):
    return f"** {inline} **"


def danoes_formula(data):
    """
    DANOE'S FORMULA
    https://en.wikipedia.org/wiki/Histogram#Doane's_formula
    """
    n = len(data)
    skewness = scipy.stats.skew(data)
    sigma_g1 = math.sqrt((6 * (n - 2)) / ((n + 1) * (n + 3)))
    num_bins = 1 + math.log(n, 2) + math.log(1 + abs(skewness) / sigma_g1, 2)
    num_bins = round(num_bins)
    return num_bins


def fit_distributions(y: List[float],
                      distributions_to_fit: Tuple[str, ...] = ['uniform', 'triang', 'expon', 'norm', 'lognorm'],
                      fitting_algorithm: str = 'RSS',
                      bins='auto',
                      alpha: float = 0.01,
                      smooth=None,
                      distributions_to_plot: int = 1):
    """
    distributions_to_fit: 'popular', 'full'

    stats 'RSS', 'wasserstein', ks': Kolmogorov-Smirnov statistic', 'energy'
    The residual sum of squares (RSS) is a statistical technique used to measure the amount of variance in a data set
    that is not explained by a model.

    bins : int, default: 'auto'

    alpha : error probability (significance level) of distribution parameters for confidence interval, prop.
    = type I error probability "false positive" - rejecting null hypothesis (when it's true)
    null hypothesis = data follows specified distribution (parameters)
    lower alpha -> larger confidence intervall (underlying limits in the data) and vice versa
    alpha = 0.0 -> no type I error, confidence intervall is 100% and all data is included as basis which
    is artificial when abstracting real world data
    """

    dfit = distfit.distfit(distr=distributions_to_fit, stats=fitting_algorithm, bins=bins, alpha=alpha, smooth=smooth)
    dfit.fit_transform(y)

    dfit.plot(chart='pdf', n_top=distributions_to_plot)
    dfit.plot(chart='cdf', n_top=distributions_to_plot)

    return dfit


def create_data(number_of_data_points: int,
                distribution_with_parameters: tuple[Any, ...],
                column_name: str, dataframe: DataFrame = None) -> DataFrame:
    distribution, *parameters = distribution_with_parameters

    new_dataframe = pd.DataFrame({column_name: [distribution(*parameters) for _ in range(number_of_data_points)]})

    if dataframe is not None:
        return pd.concat([dataframe, new_dataframe], axis=1)
    else:
        return new_dataframe


def add_noise(value, noise_lower, noise_upper):
    return value + noise_lower + (noise_upper - noise_lower) * random.random()


def add_noises(dataframe: DataFrame, noise: tuple[float, float],
               column_name: str, new_column_name: str = None) -> DataFrame:
    if new_column_name:
        dataframe[new_column_name] = dataframe[column_name]  # copy
    else:
        dataframe = dataframe.rename(columns={column_name: new_column_name})

    dataframe[new_column_name] = dataframe[new_column_name].apply(add_noise, args=noise)

    return dataframe


def write_data_to_excel(excel_file_name: str, dataframe: DataFrame, sheet_name: str, read_existing_sheet: bool = False):
    if read_existing_sheet:
        dataframe_existing: DataFrame = read_data_from_excel(excel_file_name, sheet_name)
        dataframe = pd.concat([dataframe_existing, dataframe], axis=1)

    with pd.ExcelWriter(excel_file_name, mode='a', engine='openpyxl',
                        if_sheet_exists='overlay' if read_existing_sheet else 'replace') as writer:
        dataframe.to_excel(writer, sheet_name=sheet_name, index=False)

    return dataframe


def read_data_from_excel(excel_file_name: str, sheet_name: str) -> DataFrame:
    data = pd.read_excel(excel_file_name, sheet_name=sheet_name)
    print(headline("Data Description"), "\n", data.describe())
    return data


def generate_data(excel_file_name: str, sheet_name: str, number_of_data_points: int):
    data = write_data_to_excel(excel_file_name, create_data(number_of_data_points,
                                                            (random.expovariate, 1 / 6),
                                                            "ExponentialData"), sheet_name)
    data = create_data(number_of_data_points,
                       (random.uniform, 1.0, 10.0), "UniformData", dataframe=data)
    data = add_noises(data, (-0.1, 0.1), "UniformData", "UniformDataNoise0.1")
    data = add_noises(data, (-0.3, 0.3), "UniformData", "UniformDataNoise0.3")
    data = add_noises(data, (-0.5, 0.5), "UniformData", "UniformDataNoise0.5")
    data = add_noises(data, (-1.0, 1.0), "UniformData", "UniformDataNoise1.0")

    data = create_data(number_of_data_points,
                       (random.triangular, 1.0, 10.0, 7.0), "TriangularData", dataframe=data)

    data = create_data(number_of_data_points,
                       (random.normalvariate, 5.0, 2.0), "NormData", dataframe=data)

    data = create_data(number_of_data_points,
                       (random.lognormvariate, 5.0, 2.0), "LogNormData", dataframe=data)

    write_data_to_excel(excel_file_name, data, sheet_name, False)
    return data


def print_distribution_parameters(dfit):
    print(headline("Best fitted distribution with parameters:"))

    """
    print('score: ', dfit.model['score'])
    print('name: ', dfit.model['name'])
    print('model: ', dfit.model['model'])
    print('params: ', dfit.model['params'])
    print('loc: ', dfit.model['loc'])
    print('scale: ', dfit.model['scale'])
    print('arg: ', dfit.model['arg'])
    """

    dist_name = dfit.model['name']
    loc = dfit.model['loc']
    scale = dfit.model['scale']

    print('Distribution:', dist_name)
    print("Parameters:")
    dist = getattr(scipy.stats, dist_name)

    if dist_name == "uniform":
        (min_value, max_value) = dist.interval(1.0, loc=loc, scale=scale)
        print("min:", min_value)
        print("max:", max_value)

    elif dist_name == "triang":
        # fitted parameters
        c = dfit.model['arg'][0]

        '''
        loc = left
        scale = right - left
        c = (mode - left) / (right - left)
        '''
        left = loc
        print("min:", left)
        right = scale + left
        mode = c * (right - left) + left
        print("mode:", mode)
        print("max:", right)

    elif dist_name == "expon" or dist_name == "norm":
        print("mean:", loc)
        print("stddev:", scale)

    elif dist_name == "lognorm":
        print("mean:", loc)
        print("stddev:", scale)
        print("s:", dfit.model['arg'][0])

    else:
        print("Non-'Standard' Distribution")
        print(dfit.model)

    print('CII_min_alpha (lower level confidence interval):', dfit.model['CII_min_alpha'])
    print('CII_max_alpha (higher level confidence interval):', dfit.model['CII_max_alpha'])

    print("")


def main():
    """
    "Observations"
    "Generations"
    """
    # generate_data(EXCEL_FILE_NAME, "Generations", NUMBER_OF_DATA_POINTS)

    data = read_data_from_excel(EXCEL_FILE_NAME, "Observations")

    """
    "ExponentialData"
    "UniformData"
    "UniformDataNoise0.1"
    "UniformDataNoise0.3"
    "UniformDataNoise0.5"
    "UniformDataNoise1.0"
    "TriangularData"
    "NormData"
    "LogNormData"
    """
    y = data["Data"]
    plt.plot(y, np.arange(len(y)), '.', color='black')
    df1_desc = y.describe()

    dfit = fit_distributions(y)
    plt.show()

    print_distribution_parameters(dfit)
    y_generate = dfit.generate(len(y) * 10)
    plt.plot(y_generate, np.arange(len(y_generate)), '.', color='green')
    plt.show()

    df = pd.DataFrame(data=y_generate, index=np.arange(len(y_generate))).squeeze()
    df2_desc = df.describe()

    # Print summary statistics side by side
    print("data".ljust(35) + "\t generated data")
    for stat in df1_desc.index:
        print(f"{stat.ljust(6)} : {str(df1_desc[stat]).ljust(25)} "
              f"\t {stat.ljust(6)} : {str(df2_desc[stat]).ljust(25)}"
              f"difference : {df2_desc[stat] - df1_desc[stat]}", end="")

        print("\t(median)" if stat == '50%' else "")


if __name__ == "__main__":
    main()
