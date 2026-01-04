from examples.dmpg.simio.model5_3 import setup_model_pcb
from src.core.simulation.simulation import run_replications, run_simulation
from src.core.visualization.visualization import visualize_system
from core.visualization.plots import plot_histogram, plot_box_plot, plot_scatter, plot_violin
from src.core.global_imports import Stats
import logging
import matplotlib.pyplot as plt


def main():
    run_simulation(model=setup_model_pcb, steps=900)
    visualize_system()

    run_replications(model=setup_model_pcb, steps=900, num_replications=1000, multiprocessing=False)

    plot_histogram(Stats, 'Sink', 'GoodParts', 'TimeInSystem (average)')
    plot_histogram(Stats, 'Sink', 'BadParts', 'TimeInSystem (average)')
    plot_box_plot(Stats, 'Server', 'Inspection', 'TimeProcessing (average)')
    plot_scatter(Stats, 'Sink', 'GoodParts', 'TimeInSystem (average)',
                 'Sink', 'GoodParts', 'NumberEntered',)
    plot_violin(Stats, 'Server', 'Inspection', 'ScheduledUtilization')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(module)s-%(levelname)s: %(message)s')
    logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)
    plt.set_loglevel('WARNING')

    main()
