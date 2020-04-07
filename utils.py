import networkx as nx
import numpy as np
from tqdm import tqdm
from torch.utils.data import Dataset
import json


def convert_to_cytoscape(source_path, target_path):
    """
    :param source_path: localisation of the .gpickle graph
    :param target_path: path to save the .cyjs graph
    :return: None
    """
    graph = nx.read_gpickle(source_path)
    json_graph = nx.readwrite.json_graph.cytoscape_data(graph)
    with open(target_path + ".cyjs", "w") as json_file:
        json.dump(json_graph, json_file)


class PPInteraction_dataset(Dataset):
    """
    Extract interaction data from graph an creates a torch dataset
    """

    def __init__(self, graph, directed, score_threshold, node_attribute, regression, no_interactions_ratio = 1.0):
        """
        :param graph: the directed or undirected graph to create the data from
        :param directed: True if directed else False
        :param score_threshold: threshold on scores in edges
        :param node_attribute: the type of node label to extract from graph (ex "sequence", "cellular_components", "info"...)
                            see notebook node attributes
        :param regression: True if regression task (keep scores) or False in classification (existing edge will be 1.0)
        :param no_interactions_ratio: float between 0 and 1 controling amount of no_interaction data to create
        """
        if directed:
            edges = [
                (x, y, z["link"], z["score"])
                for x, y, z in graph.edges(data=True)
                if z["score"] >= score_threshold
            ]
            data = []
            for prot_a, prot_b, link, score in edges:
                prot_a_data = graph.nodes(data=True)[prot_a][node_attribute]
                prot_b_data = graph.nodes(data=True)[prot_b][node_attribute]
                if regression:
                    data.append((prot_a_data, prot_b_data, link, score))
                else:
                    data.append((prot_a_data, prot_b_data, link, 1.0))
        else:
            edges = [
                (x, y, z["score"])
                for x, y, z in graph.edges(data=True)
                if z["score"] >= score_threshold
            ]
            data = []
            for prot_a, prot_b, score in edges:
                prot_a_data = graph.nodes(data=True)[prot_a][node_attribute]
                prot_b_data = graph.nodes(data=True)[prot_b][node_attribute]
                if regression:
                    data.append((prot_a_data, prot_b_data, score))
                else:
                    data.append((prot_a_data, prot_b_data, 1.0))
        self.data = data
        nodes = list(graph.nodes())
        no_data = []
        sampled = []
        num_no_labels = int(no_interactions_ratio * len(data))
        for _ in tqdm(range(num_no_labels)):
            prot_a = np.random.choice(nodes)
            prot_b = np.random.choice(nodes)
            while (
                (prot_a, prot_b) in graph.edges()
                or (prot_b, prot_a) in graph.edges()
                or (prot_b, prot_a) in sampled
                or (prot_a, prot_b) in sampled
            ):
                prot_a = np.random.choice(nodes)
                prot_b = np.random.choice(nodes)
            prot_a_data = graph.nodes(data=True)[prot_a][node_attribute]
            prot_b_data = graph.nodes(data=True)[prot_b][node_attribute]
            if directed:
                no_data.append((prot_a_data, prot_b_data, "not_linked", 0.0))
            else:
                no_data.append((prot_a_data, prot_b_data, 0.0))
            sampled.append((prot_a, prot_b))
        self.data.extend(no_data)

    def __getitem__(self, ix):
        return self.data[ix]

    def __len__(self):
        return len(self.data)
