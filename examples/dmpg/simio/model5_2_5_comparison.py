from examples.dmpg.simio.model5_2_5 import setup_model5_2
from examples.dmpg.simio.model5_2_5_arrival_table import setup_model_pcb_with_arrival_table
from src.core.simulation.simulation import run_replications, run_simulation

import logging
import matplotlib.pyplot as plt


def main():
    run_simulation(model=setup_model5_2, steps=900)

    # run_simulation(model=setup_model_pcb_with_breakdowns, steps=900)

    run_simulation(model=setup_model_pcb_with_arrival_table, steps=900)

    run_replications(model=setup_model5_2, steps=900, num_replications=1000, multiprocessing=False)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(module)s-%(levelname)s: %(message)s')
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    plt.set_loglevel('WARNING')

    main()
