import warnings

from graphviz import Digraph

from src.core.types.node_type import NodeType
from src.core.components.combiner import Combiner
from src.core.components.logistic.storage import Storage
from src.core.components.separator import Separator
from src.core.components.server import Server
from src.core.components.sink import Sink
from src.core.components.source import Source

warnings.simplefilter(action='ignore', category=FutureWarning)


class Visualization:
    """
    Creates a visualization of a simulaiton model in graphviz.
    """
    def __init__(self,
                 model_name: str = None,
                 abstraction: dict[str: list[str]] = None,
                 dot_att: list[dict[str:str]] = None,
                 pivot_data: dict[list[str]] = None,):
        """
        Initalizaiton of a new visualization.

        :param model_name: Name for the model.
        :param abstraction: Dictionary that contaions the name of the abstracionts as keys and a list of nodes,
        that to be part of the abstraction, as values.
        :param dot_att: List of dictionaries that contain the configurations of dot attributes.
        :param pivot_data: List of dictionaries that contain the configurations of pivot attributes that will be shown
        at the nodes in the model.
        """
        if model_name:
            self.model_name = model_name
        else:
            self.model_name = 'Simulation Model'

        if pivot_data:
            self.pivot_data = pivot_data
        else:
            # default data to present
            self.pivot_data = {
                NodeType.SOURCE: ['total_entities_processed_pivot_table'],
                NodeType.SERVER: ['total_entities_processed_pivot_table'],
                NodeType.STORAGE: ['total_entities_processed_pivot_table'],
                NodeType.COMBINER: ['total_entities_processed_pivot_table'],
                NodeType.SEPARATOR: ['total_entities_processed_pivot_table'],
                NodeType.ABSTRACTION: ['total_entities_processed_pivot_table'],
                NodeType.SINK: ['entities_processed']
            }

        self.nodes = {
            NodeType.SOURCE: [],
            NodeType.SERVER: [],
            NodeType.STORAGE: [],
            NodeType.COMBINER: [],
            NodeType.SEPARATOR: [],
            NodeType.ABSTRACTION: [],
            NodeType.SINK: []
        }

        # default style for the nodes & connections
        self.style = {
            NodeType.SOURCE: {'shape': 'diamond',
                              'fillcolor': '#BDD7EE',
                              'fontcolor': 'black'},
            NodeType.SERVER: {'shape': 'box'},
            NodeType.STORAGE: {'shape': 'box'},
            NodeType.COMBINER: {'shape': 'box'},
            NodeType.SEPARATOR: {'shape': 'box'},
            NodeType.ABSTRACTION: {'shape': 'box'},
            NodeType.SINK: {'shape': 'hexagon',
                            'fillcolor': '#E6B8AF',
                            'fontcolor': 'black'},
            'connection': {'color': 'darkblue',
                           'style': 'solid', },
        }

        self._collect_data = {
            NodeType.SOURCE: {},
            NodeType.SERVER: {},
            NodeType.STORAGE: {},
            NodeType.COMBINER: {},
            NodeType.SEPARATOR: {},
            NodeType.ABSTRACTION: {},
            NodeType.SINK: {}
        }

        if dot_att:
            self.dot_att = dot_att
        else:
            # default attributes
            self.dot_att = [
                {'rankdir': 'LR', 'size': '24,14', 'newrank': 'true'},
                {'fontname': 'Open Sans', 'fontsize': '12', 'fontcolor': 'grey'},
                {'kw': 'node', 'style': 'filled, rounded', 'color': 'lightgrey', 'fontname': 'Open Sans', 'fontsize': '11'},
                {'kw': 'edge', 'arrowhead': 'vee', 'arrowsize': '0.8', 'color': 'grey', 'fontname': 'Open Sans', 'fontsize': '10'},
                {'overlap': 'scalexy', 'splines': 'true', 'nodesep': '0.6', 'ranksep': '2.0', 'bgcolor': 'whitesmoke'}
            ]

        self.connections = []
        self.number_processed = {}
        self.connection_probalities = {}

        self.abstraction = abstraction
        self.dot: Digraph = Digraph(comment=self.model_name)

        self.global_max = 0

    def save_graph(self, formats: list[str], filepath: str) -> None:
        """
        Saves graph to file.

        :param formats: The Formats the graph will be saved in.
        :param filepath: Path to the savefile.
        :return: None
        """
        if formats:
            for f in formats:
                self.dot.render(filepath, view=False, format=f)
            else:
                self.dot.render(filepath, view=True)

    def _is_abstracted(self, node_name: str) -> tuple[bool, str]:
        """
        Checks if a node is part of an abstraction.

        :param node_name: Name of the node to check.
        :return: A tuple with boolean and the name of the abstraction if it is part of an abstraction and false
        and None otherwise.
        """
        for key in self.abstraction:
            if node_name in self.abstraction[key]:
                return True, key
        return False, None

    def _create_connection(self, start: str, end: str) -> tuple[str, str]:
        """
        Creates a connection for the graph and checking if the connection contaions any nodes that
        are linked to an abstraction.

        :param start: Name of the start node.
        :param end: Name of the end node.
        :return: Tuple with the name of the start and end node.
        """
        if self.abstraction:
            # check if start or end is in abstraction
            result_start = self._is_abstracted(start)
            result_end = self._is_abstracted(end)

            if result_start[0] and result_end[0] and result_start[1] != result_end[1]:
                return result_start[1], result_end[1]

            if result_start[0] and not result_end[0]:
                return result_start[1], end

            if not result_start[0] and result_end[0]:
                return start, result_end[1]

            if not result_start[0] and not result_end[0]:
                return start, end

        else:
            return start, end

    def _add_connection(self, connection: tuple[str, str, float]) -> None:
        """
        Add a connection to the graph if it is not existing, and calculates the frequency.

        :param connection: A tuple with the infromation about start, end and frequency of the connection.
        :return: None
        """
        if connection[0:2] in self.connections:
            if self.connection_probalities[connection[0:2]] is not None:
                self.connection_probalities[connection[0:2]] += connection[2]
        else:
            self.connections.append(connection[0:2])
            self.connection_probalities[connection[0:2]] = connection[2]

    def _add_node(self, node: str, total_processed: int, node_type: NodeType):
        if node in self.nodes[node_type]:
            self.number_processed[node] += total_processed
        else:
            self.nodes[node_type].append(node)
            self.number_processed[node] = total_processed

    def _draw_connections(self) -> None:
        """
        Draws the connections into the graphviz graph.

        :return: None
        """
        for connection in self.connections:
            if self.connection_probalities[connection] is not None:
                prob = self.connection_probalities[connection]
                edge_label = f'{prob:.1f}%' if prob else ''
            else:
                edge_label = ''
            self.dot.edge(connection[0], connection[1], label=edge_label, **self.style['connection'])

    def _draw_nodes(self) -> None:
        """
        Draws the nodes into the graphviz graph.

        :return: None
        """
        for node_type in self.nodes.keys():
            for node in self.nodes[node_type]:
                if node_type == NodeType.SOURCE:
                    label = f'{node}\nCreated: {self.number_processed[node]}'
                else:
                    label = f'{node}\nProcessed: {self.number_processed[node]}'

                if 'fillcolor' in self.style[node_type]:
                    self.dot.node(node, label=label, **self.style[node_type])
                else:
                    color = self._get_color(self.number_processed[node], self.global_max)
                    self.dot.node(node, label=label, fillcolor=color, **self.style[node_type])

    def _get_values(self, node: object, node_name: str, node_type: NodeType, abstraction: bool = False):
        self._collect_data[node_type][node_name] = {}
        for data_to_collect in self.pivot_data[node_type]:
            if abstraction:
                if data_to_collect in self._collect_data[node_type][node_name]:
                    self._collect_data[node_type][node_name][data_to_collect].append(getattr(node, data_to_collect))
                else:
                    self._collect_data[node_type][node_name][data_to_collect] = [getattr(node, data_to_collect)]
            else:
                self._collect_data[node_type][node_name][data_to_collect] = getattr(node, data_to_collect)

    def _create_nodes_and_connections(self, node_list: list, node_type: NodeType) -> None:
        """
        Creartes all nodes and there conncetions for a given list of nodes.

        :param node_list: List of nodes that will be added to the graph.
        :param node_type: Type of the nodes in the list.
        :return: None.
        """
        for node in node_list:
            if self.abstraction:
                result = self._is_abstracted(node.name)
                if result[0]:
                    self._add_node(result[1], node.total_entities_processed_pivot_table, NodeType.ABSTRACTION)
                    self._get_values(node, node.name, node_type, abstraction=True)
                else:
                    self._add_node(node.name, node.total_entities_processed_pivot_table, node_type)
                    self._get_values(node, node.name, node_type)
            else:
                self._add_node(node.name, node.total_entities_processed_pivot_table, node_type)
                self._get_values(node, node.name, node_type)

            for next_component, prob, *_ in node.next_components:
                connection = self._create_connection(node.name, next_component.name)
                if connection:
                    self._add_connection((connection[0], connection[1], prob))

    @staticmethod
    def _get_color(value: int, max_value: int) -> str:
        """
        Converts the value into a color between blue and red.

        :param value: Value to be converted to color.
        :param max_value: Maximum value in the range.
        :return: Color in the hexadecimal format.
        """

        if max_value == 0:
            return "#0000ff"  # If max value is 0 retrun blue

        ratio = value / max_value

        r = int(255 * ratio)
        g = 0
        b = int(255 * (1 - ratio))

        return f"#{r:02x}{g:02x}{b:02x}"

    def _create_sources_and_connections(self):
        for source in Source.sources:
            self._add_node(source.name, source.entities_created_pivot_table, NodeType.SOURCE)
            for next_component, prob, *_ in source.next_components:
                connection = self._create_connection(source.name, next_component.name)
                if connection:
                    self._add_connection((connection[0], connection[1], prob))

    def _create_sinks(self):
        for sink in Sink.sinks:
            self._add_node(sink.name, sink.entities_processed, NodeType.SINK)

    def visualize_model(self) -> None:
        """
        Turns the model into a graph.
        """

        # Advanced graph style attributes for an elegant look
        for att in self.dot_att:
            self.dot.attr(**att)

        max_server = max(server.total_entities_processed_pivot_table for server in Server.servers) if Server.servers else 1
        max_storage = max(storage.total_entities_processed_pivot_table for storage in Storage.storages) if Storage.storages else 1
        max_combiner = max(combiner.total_entities_processed_pivot_table for combiner in Combiner.combiners) if Combiner.combiners else 1
        max_separator = max(seperator.total_entities_processed_pivot_table for seperator in Separator.separators) if Separator.separators else 1

        self.global_max = max(max_server, max_storage, max_combiner, max_separator)

        self._create_sources_and_connections()
        self._create_nodes_and_connections(Server.servers, NodeType.SERVER,)
        self._create_nodes_and_connections(Storage.storages, NodeType.STORAGE)
        self._create_nodes_and_connections(Combiner.combiners, NodeType.COMBINER)
        self._create_nodes_and_connections(Separator.separators, NodeType.SEPARATOR)
        self._create_sinks()

        self._draw_nodes()
        self._draw_connections()


def visualize_system(file: str = "visualize_model"):
    visu = Visualization()
    visu.visualize_model()

    visu.save_graph(['svg'], f'{file}')
