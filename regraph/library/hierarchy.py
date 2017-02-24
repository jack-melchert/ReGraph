"""."""
import itertools
import copy
import os
import json

import networkx as nx
# import copy

from networkx.algorithms import isomorphism
from regraph.library.category_op import (pullback,
                                         pullback_complement,
                                         pushout,
                                         nary_pullback)
from regraph.library.primitives import (get_relabeled_graph,
                                        get_edge,
                                        add_node,
                                        add_edge,
                                        graph_to_json,
                                        graph_from_json,
                                        print_graph)
from regraph.library.utils import (compose_homomorphisms,
                                   check_homomorphism,
                                   is_subdict,
                                   keys_by_value,
                                   normalize_attrs,
                                   to_set)
from regraph.library.rules import Rule


class AttributeContainter(object):
    """Abstract class for a container with attributes."""

    def add_attrs(self, attrs):
        """Add attrs to the graph node."""
        if attrs:
            new_attrs = copy.deepcopy(attrs)
            normalize_attrs(new_attrs)
        else:
            new_attrs = dict()
        if len(self.attrs) == 0:
            self.attrs = new_attrs
        else:
            for key, value in new_attrs.items():
                if key not in self.attrs.keys():
                    self.attrs.update({key: to_set(value)})
                else:
                    self.attrs[key] =\
                        self.attrs[key].union(to_set(value))
        return

    def remove_attrs(self, attrs):
        """Remove attributes."""
        normalize_attrs(self.attrs)
        for key, value in attrs.items():
            if key not in self.attrs.keys():
                pass
                # warnings.warn(
                #     "Node '%s' does not have attribute '%s'!" %
                #     (str(node), str(key)), RuntimeWarning)
            else:
                elements_to_remove = []
                for el in to_set(value):
                    if el in self.attrs[key]:
                        elements_to_remove.append(el)
                    else:
                        pass
                        # warnings.warn(
                        #     "Node '%s' does not have attribute '%s' with value '%s'!" %
                        #     (str(node), str(key), str(el)), RuntimeWarning)
                for el in elements_to_remove:
                    self.attrs[key].remove(el)

    def update_attrs(self, attrs):
        """Update attribures."""
        new_attrs = copy.deepcopy(attrs)
        if new_attrs is None:
            pass
        else:
            normalize_attrs(new_attrs)
            self.attrs = new_attrs


class GraphNode(AttributeContainter):
    """Data structure incapsulating graph in the node of the hierarchy."""

    def __init__(self, graph, attrs=None):
        """Initialize graph node with graph object and attrs."""
        self.graph = graph
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return


class RuleNode(AttributeContainter):
    """Data structure incapsulating a rule in the node of the hierarchy."""

    def __init__(self, rule, attrs=None):
        """Initialize rule with a Rule object."""
        self.rule = rule
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return


class Typing(AttributeContainter):
    """Incapsulate homomorphism in the edge of the hierarchy."""

    def __init__(self, mapping, ignore_attrs=False, attrs=None):
        """Initialize homomorphism."""
        self.mapping = mapping
        self.ignore_attrs = ignore_attrs
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return


class RuleTyping(AttributeContainter):
    """Incapsulate rule typing in the edge of the hierarchy."""

    def __init__(self, lhs_mapping, rhs_mapping,
                 ignore_attrs=False, attrs=None):
        """Initialize homomorphism."""
        self.lhs_mapping = lhs_mapping
        self.rhs_mapping = rhs_mapping
        self.ignore_attrs = ignore_attrs
        if attrs:
            self.attrs = attrs
        else:
            self.attrs = dict()
        return


class Hierarchy(nx.DiGraph):
    """."""

    def __init__(self, directed=True, graph_node_constuctor=GraphNode):
        """Initialize an hierarchy of graphs."""
        nx.DiGraph.__init__(self)
        self.hierarchy_attrs = dict()
        self.directed = directed
        self.graph_node_constructor = graph_node_constuctor
        return

    def __str__(self):
        """Print the hierarchy."""
        res = ""
        res += "\nGraphs (directed == %s): \n" % self.directed
        res += "\nNodes:\n"
        for n in self.nodes():
            if isinstance(self.node[n], GraphNode):
                res += "Graph:"
            elif type(self.node[n]) == RuleNode:
                res += "Rule:"
            else:
                raise ValueError(
                    "Hierarchy error: unknown type '%s' of the node '%s'!" %
                    (type(self.node[n]), n)
                )
            res += " " + str(n) + " " +\
                str(self.node[n].attrs) + "\n"
        res += "\n"
        res += "Typing homomorphisms: \n"
        for n1, n2 in self.edges():
            if type(self.edge[n1][n2]) == Typing:
                res += "%s -> %s: ignore_attrs == %s\n" %\
                    (n1, n2, self.edge[n1][n2].ignore_attrs)
                res += "mapping: %s\n" % str(self.edge[n1][n2].mapping)
            elif type(self.edge[n1][n2]) == RuleTyping:
                res += "%s -> %s: ignore_attrs == %s\n" %\
                    (n1, n2, self.edge[n1][n2].ignore_attrs)
                res += "lhs mapping: %s\n" % str(self.edge[n1][n2].lhs_mapping)
                res += "rhs mapping: %s\n" % str(self.edge[n1][n2].rhs_mapping)
            else:
                raise ValueError(
                    "Hierarchy error: unknown type '%s' of the edge '%s->%s'!" %
                    (type(self.edge[n1][n2]), n1, n2)
                )

        res += "\n"
        res += "attributes : \n"
        res += str(self.hierarchy_attrs)
        res += "\n"

        return res

    def add_graph(self, graph_id, graph, graph_attrs=None):
        """Add graph to the hierarchy."""
        if self.directed != graph.is_directed():
            if self.directed:
                raise ValueError(
                    "Hierarchy is defined for directed == %s graphs!" %
                    self.directed
                )
            else:
                raise ValueError("Hierarchy is defined for undirected graphs!")
        if graph_id in self.nodes():
            raise ValueError(
                "Node '%s' already exists in the hierarchy!" %
                graph_id
            )
        self.add_node(graph_id)
        self.node[graph_id] = self.graph_node_constructor(graph, graph_attrs)
        return

    def add_rule(self, rule_id, rule, rule_attrs=None):
        """Add rule to the hierarchy."""
        if self.directed != rule.lhs.is_directed():
            raise ValueError(
                "Hierarchy is defined for directed == %s graphs: " +
                "lhs of the rule is directed == %s!" %
                (self.directed, rule.lhs.is_directed())
            )
        if self.directed != rule.p.is_directed():
            raise ValueError(
                "Hierarchy is defined for directed == %s graphs: " +
                "p of the rule is directed == %s!" %
                (self.directed, rule.p.is_directed())
            )
        if self.directed != rule.rhs.is_directed():
            raise ValueError(
                "Hierarchy is defined for directed == %s graphs: " +
                "rhs of the rule is directed == %s!" %
                (self.directed, rule.rhs.is_directed())
            )
        if rule_id in self.nodes():
            raise ValueError(
                "Node '%s' already exists in the hierarchy!" %
                rule_id
            )
        self.add_node(rule_id)
        self.node[rule_id] = RuleNode(rule, rule_attrs)

    def add_typing(self, source, target, mapping, ignore_attrs=False, attrs=None):
        """Add homomorphism to the hierarchy."""
        if source not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % source)
        if target not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % target)

        if not isinstance(self.node[source], GraphNode):
            if type(self.node[source]) == RuleNode:
                raise ValueError(
                    "Source node is a rule, use `add_rule_typing` method instead!"
                )
            else:
                raise ValueError(
                    "Source of a typing should be a graph, `%s` is provided!" %
                    type(self.node[source])
                )
        if not isinstance(self.node[target], GraphNode):
            raise ValueError(
                "Target of a typing should be a graph, `%s` is provided!" %
                type(self.node[target])
            )

        # check no cycles are produced
        self.add_edge(source, target)
        if not nx.is_directed_acyclic_graph(self):
            self.remove_edge(source, target)
            raise ValueError(
                "Edge '%s->%s' creates a cycle in the hierarchy!" %
                (source, target)
            )
        self.remove_edge(source, target)

        # check if the homomorphism is valid
        check_homomorphism(
            self.node[source].graph,
            self.node[target].graph,
            mapping,
            ignore_attrs
        )

        # check if commutes with other shortest paths from source to target

        paths = nx.all_shortest_paths(self, source, target)
        try:
            for p in paths:
                s = p[0]
                t = p[1]
                homomorphism = self.edge[s][t].mapping
                for i in range(2, len(p)):
                    s = p[i - 1]
                    t = p[i]
                    homomorphism = compose_homomorphisms(
                        self.edge[s][t].mapping,
                        homomorphism
                    )
                if homomorphism != mapping:
                    raise ValueError(
                        "Homomorphism does not commute with an existing " +
                        "path from '%s' to '%s'!" % (source, target))
        except(nx.NetworkXNoPath):
            pass

        self.add_edge(source, target)
        self.edge[source][target] = Typing(mapping, ignore_attrs, attrs)
        return

    def add_partial_typing(self, source, target,
                           mapping, ignore_attrs=False, attrs=None):
        """Add partial homomorphism A -> B."""
        # 1. Construct A' (A' >-> A)
        if self.is_directed:
            new_graph = nx.DiGraph()
        else:
            new_graph = nx.Graph()

        if not isinstance(self.node[source], GraphNode):
            if type(self.node[source]) == RuleNode:
                raise ValueError(
                    "Source node is a rule, use `add_rule_typing` method instead!"
                )
            else:
                raise ValueError(
                    "Source of a typing should be a graph, `%s` is provided!" %
                    type(self.node[source])
                )
        if not isinstance(self.node[target], GraphNode):
            raise ValueError(
                "Target of a typing should be a graph, `%s` is provided!" %
                type(self.node[target])
            )

        new_graph_source = {}
        for node in self.node[source].graph.nodes():
            if node in mapping.keys():
                add_node(new_graph, node, self.node[source].graph.node[node])
                new_graph_source[node] = node

        for s, t in self.node[source].graph.edges():
            if s in new_graph.nodes() and t in new_graph.nodes():
                add_edge(new_graph, s, t, get_edge(self.node[source].graph, s, t))
        new_graph_attrs = copy.deepcopy(self.node[source].attrs)

        # generate_name for the new_graph
        new_name = str(source) + "_" + str(target)
        if new_name in self.nodes():
            i = 1
            new_name = str(source) + "_" + str(target) + str(i)
            while new_name in self.nodes():
                i += 1
                new_name = str(source) + "_" + str(target) + str(i)

        new_graph_target = dict(
            [(node, mapping[node]) for node in new_graph.nodes()]
        )
        self.add_graph(new_name, new_graph, new_graph_attrs)
        self.add_typing(new_name, source, new_graph_source, False, attrs)
        self.add_typing(new_name, target, new_graph_target, ignore_attrs, attrs)
        return

    def add_rule_typing(self, rule_id, graph_id, lhs_mapping, rhs_mapping,
                        ignore_attrs=False, attrs=None):
        """Add typing of a rule."""
        if rule_id not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % rule_id)
        if graph_id not in self.nodes():
            raise ValueError(
                "Node '%s' is not defined in the hierarchy!" % graph_id)

        if type(self.node[rule_id]) != RuleNode:
            raise ValueError(
                "Source of a rule typing should be a rule, `%s` is provided!" %
                type(self.node[rule_id])
            )
        if not isinstance(self.node[graph_id], GraphNode):
            raise ValueError(
                "Target of a rule typing should be a graph, `%s` is provided!" %
                type(self.node[graph_id])
            )
        # check if an lhs typing is valid
        check_homomorphism(
            self.node[rule_id].rule.lhs,
            self.node[graph_id].graph,
            lhs_mapping,
            ignore_attrs
        )
        # check if an rhs typing is valid
        check_homomorphism(
            self.node[rule_id].rule.rhs,
            self.node[graph_id].graph,
            rhs_mapping,
            ignore_attrs
        )
        self.add_edge(rule_id, graph_id)
        self.edge[rule_id][graph_id] = RuleTyping(
            lhs_mapping,
            rhs_mapping,
            ignore_attrs,
            attrs
        )
        return

    def remove_graph(self, graph_id, reconnect=False):
        """Remove graph from the hierarchy.

        If `reconnect`, map the children homomorphisms
        of this graph to its parents.
        """
        if graph_id not in self.nodes():
            raise ValueError(
                "Graph `%s` is not defined in the hierarchy!" % graph_id)

        if reconnect:
            out_graphs = self.successors(graph_id)
            in_graphs = self.predecessors(graph_id)

            for source in in_graphs:
                for target in out_graphs:
                    if type(self.edge[source][graph_id]) == RuleTyping:
                        lhs_mapping = compose_homomorphisms(
                            self.edge[graph_id][target].mapping,
                            self.edge[source][graph_id].lhs_mapping
                        )
                        rhs_mapping = compose_homomorphisms(
                            self.edge[graph_id][target].mapping,
                            self.edge[source][graph_id].rhs_mapping
                        )
                        if (source, target) not in self.edges():
                            self.add_rule_typing(
                                source,
                                target,
                                lhs_mapping,
                                rhs_mapping,
                                self.edge[source][graph_id].ignore_attrs or
                                self.edge[graph_id][target].ignore_attrs
                            )
                    else:
                        # compose two homomorphisms
                        mapping = compose_homomorphisms(
                            self.edge[graph_id][target].mapping,
                            self.edge[source][graph_id].mapping
                        )

                        if (source, target) not in self.edges():
                            self.add_typing(
                                source,
                                target,
                                mapping,
                                self.edge[source][graph_id].ignore_attrs or
                                self.edge[graph_id][target].ignore_attrs
                            )

        self.remove_node(graph_id)

    def node_type(self, graph_id, node_id):
        """Get a list of the immediate types of a node."""
        if graph_id not in self.nodes():
            raise ValueError(
                "Graph '%s' is not defined in the hierarchy!"
                % graph_id
            )
        if node_id not in self.node[graph_id].graph.nodes():
            raise ValueError(
                "Graph '%s' does not have a node with id '%s'!"
                % (graph_id, node_id)
            )
        types = []
        for _, typing in self.out_edges(graph_id):
            mapping = self.edge[graph_id][typing].mapping
            types.append(mapping[node_id])
        return types

    def find_matching(self, graph_id, pattern, pattern_typing=None):
        """Find an instance of a pattern in a specified graph.

        `graph_id` -- id of a graph in the hierarchy to search for matches;
        `pattern` -- nx.(Di)Graph object defining a pattern to match;
        `pattern_typing` -- a dictionary that specifies a typing of a pattern,
        keys of the dictionary -- graph id that types a pattern, this graph
        should be among parents of the `graph_id` graph; values are mappings
        of nodes from pattern to the typing graph;
        """

        if type(self.node[graph_id]) == RuleNode:
            raise ValueError("Pattern matching in a rule is not implemented!")
        # Check that 'typing_graph' and 'pattern_typing' are correctly specified
        if len(self.successors(graph_id)) != 0:
            if pattern_typing is None:
                raise ValueError(
                    "Graph '%s' has non-empty set of parents, " +
                    "pattern should be typed by one of them!" %
                    graph_id
                )
            # Check 'typing_graph' is in successors of 'graph_id'
            for typing_graph, _ in pattern_typing.items():
                if typing_graph not in self.successors(graph_id):
                    raise ValueError(
                        "Pattern typing graph '%s' is not in the typing graphs of '%s'!" %
                        (typing_graph, graph_id)
                    )
            # Check pattern typing is a valid homomorphism
            for typing_graph, (mapping, ignore_attrs) in pattern_typing.items():
                check_homomorphism(
                    pattern,
                    self.node[typing_graph].graph,
                    mapping,
                    ignore_attrs
                )

        labels_mapping = dict(
            [(n, i + 1) for i, n in enumerate(self.node[graph_id].graph.nodes())])
        g = get_relabeled_graph(self.node[graph_id].graph, labels_mapping)

        inverse_mapping = dict(
            [(value, key) for key, value in labels_mapping.items()]
        )

        if pattern_typing:
            g_typing = dict([
                (typing_graph, dict([
                    (labels_mapping[k], v) for k, v in self.edge[graph_id][typing_graph].mapping.items()
                ])) for typing_graph in pattern_typing.keys()
            ])

        matching_nodes = set()

        # Find all the nodes matching the nodes in a pattern
        for pattern_node in pattern.nodes():
            for node in g.nodes():
                if pattern_typing:
                    # check types match
                    match = False
                    for typing_graph, (typing, _) in pattern_typing.items():
                        if g_typing[typing_graph][node] == typing[pattern_node]:
                            if is_subdict(pattern.node[pattern_node], g.node[node]):
                                match = True
                    if match:
                        matching_nodes.add(node)
                else:
                    if is_subdict(pattern.node[pattern_node], g.node[node]):
                        matching_nodes.add(node)
        reduced_graph = g.subgraph(matching_nodes)
        instances = []
        isomorphic_subgraphs = []
        for sub_nodes in itertools.combinations(reduced_graph.nodes(),
                                                len(pattern.nodes())):
                subg = reduced_graph.subgraph(sub_nodes)
                for edgeset in itertools.combinations(subg.edges(),
                                                      len(pattern.edges())):
                    if g.is_directed():
                        edge_induced_graph = nx.DiGraph(list(edgeset))
                        edge_induced_graph.add_nodes_from(
                            [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                        matching_obj = isomorphism.DiGraphMatcher(pattern, edge_induced_graph)
                        for isom in matching_obj.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))
                    else:
                        edge_induced_graph = nx.Graph(edgeset)
                        edge_induced_graph.add_nodes_from(
                            [n for n in subg.nodes() if n not in edge_induced_graph.nodes()])
                        matching_obj = isomorphism.GraphMatcher(pattern, edge_induced_graph)
                        for isom in matching_obj.isomorphisms_iter():
                            isomorphic_subgraphs.append((subg, isom))

        for subgraph, mapping in isomorphic_subgraphs:
            # Check node matches
            # exclude subgraphs which nodes information does not
            # correspond to pattern
            for (pattern_node, node) in mapping.items():
                if pattern_typing:
                    for typing_graph, (typing, _) in pattern_typing.items():
                        if g_typing[typing_graph][node] != typing[pattern_node]:
                            break
                        if not is_subdict(pattern.node[pattern_node], subgraph.node[node]):
                            break
                    else:
                        continue
                    break
            else:
                # check edge attribute matched
                for edge in pattern.edges():
                    pattern_attrs = get_edge(pattern, edge[0], edge[1])
                    target_attrs = get_edge(subgraph, mapping[edge[0]], mapping[edge[1]])
                    if not is_subdict(pattern_attrs, target_attrs):
                        break
                else:
                    instances.append(mapping)

        # Bring back original labeling

        for instance in instances:
            for key, value in instance.items():
                instance[key] = inverse_mapping[value]

        return instances

    def rewrite(self, graph_id, instance, rule,
                lhs_typing=None, rhs_typing=None):
        """Rewrite and propagate the changes up."""
        # 0. Check consistency of the input parameters &
        # validity of homomorphisms
        if type(self.node[graph_id]) == RuleNode:
            raise ValueError("Rewriting of a rule is not implemented!")
        for typing_graph, (mapping, ignore_attrs) in lhs_typing.items():
            check_homomorphism(
                rule.lhs,
                self.node[typing_graph].graph,
                mapping,
                ignore_attrs
            )
        for typing_graph, (mapping, ignore_attrs) in rhs_typing.items():
            check_homomorphism(
                rule.rhs,
                self.node[typing_graph].graph,
                mapping,
                ignore_attrs
            )

        # 1. Rewriting steps
        g_m, p_g_m, g_m_g = pullback_complement(
            rule.p,
            rule.lhs,
            self.node[graph_id].graph,
            rule.p_lhs,
            instance
        )
        g_prime, g_m_g_prime, r_g_prime = pushout(
            rule.p,
            g_m,
            rule.rhs,
            p_g_m,
            rule.p_rhs
        )

        # set g_prime for the 'graph_id' node
        updated_graphs = {
            graph_id: (g_m, g_m_g, g_prime, g_m_g_prime)
        }
        updated_homomorphisms = {}
        removed_homomorphisms = set()

        for typing_graph in self.successors(graph_id):
            if typing_graph not in rhs_typing.keys():
                # check if there are anything added or merged
                removed_homomorphisms.add((graph_id, typing_graph))
                # self.remove_edge(graph_id, typing_graph)
            else:
                new_nodes = {}
                removed_nodes = set()
                new_hom = copy.deepcopy(self.edge[graph_id][typing_graph].mapping)
                for node in rule.lhs.nodes():
                    p_keys = keys_by_value(rule.p_lhs, node)
                    # nodes that were removed
                    if len(p_keys) == 0:
                        removed_nodes.add(node)
                    # nodes that were cloned
                    elif len(p_keys) > 1:
                        for k in p_keys:
                            new_nodes[p_g_m[k]] =\
                                lhs_typing[typing_graph][0][node]
                for node in rule.rhs.nodes():
                    p_keys = keys_by_value(rule.p_rhs, node)
                    # nodes that were added
                    if len(p_keys) == 0:
                        new_nodes.update({
                            node: rhs_typing[typing_graph][0][node]
                        })
                    # nodes that were merged
                    elif len(p_keys) > 1:
                        removed_nodes.update(set([
                            instance[rule.p_lhs[k]] for k in p_keys
                        ]))
                        new_nodes.update({
                            node: rhs_typing[typing_graph][0][node]
                        })
                # update homomorphisms
                for n in removed_nodes:
                    del new_hom[n]
                new_hom.update(new_nodes)
                ignore_attrs = rhs_typing[typing_graph][1]
                updated_homomorphisms.update({
                    (graph_id, typing_graph): (new_hom, ignore_attrs)
                })

        # 2. Propagation steps reverse BFS on neighbours
        current_level = set(self.predecessors(graph_id))
        successors = dict([
            (n, [graph_id]) for n in current_level
        ])

        while len(current_level) > 0:
            next_level = set()
            for graph in current_level:
                # print("gonna propagate here: %s", graph)
                # print(successors)
                # make changes to the graph
                if len(successors[graph]) == 1:
                    # simple case
                    suc = successors[graph][0]
                    if isinstance(self.node[graph], GraphNode):
                        if suc in updated_graphs.keys():
                            # find pullback
                            graph_m, graph_m_graph, graph_m_suc_m =\
                                pullback(
                                    self.node[graph].graph,
                                    updated_graphs[suc][0],
                                    self.node[suc].graph,
                                    self.edge[graph][suc].mapping,
                                    updated_graphs[suc][1]
                                )
                            updated_graphs.update({
                                graph: (graph_m, graph_m_graph, None, None)
                            })
                            updated_homomorphisms.update({
                                (graph, suc): (
                                    graph_m_suc_m,
                                    self.edge[graph][suc].ignore_attrs
                                )
                            })
                    elif type(self.node[graph]) == RuleNode:
                        # propagation to lhs
                        lhs_m, lhs_m_lhs, lhs_m_suc_m =\
                            pullback(
                                self.node[graph].rule.lhs,
                                updated_graphs[suc][0],
                                self.node[suc].graph,
                                self.edge[graph][suc].lhs_mapping,
                                updated_graphs[suc][1]
                            )
                        # propagation to p
                        p_mapping = {}
                        for node in self.node[graph].rule.p.nodes():
                            p_mapping[node] =\
                                self.edge[graph][suc].lhs_mapping[self.node[graph].rule.p_lhs[node]]
                        p_m, p_m_p, _ =\
                            pullback(
                                self.node[graph].rule.p,
                                updated_graphs[suc][0],
                                self.node[suc].graph,
                                p_mapping,
                                updated_graphs[suc][1]
                            )
                        # propagation to rhs
                        rhs_m, rhs_m_rhs, rhs_m_suc_m =\
                            pullback(
                                self.node[graph].rule.rhs,
                                updated_graphs[suc][0],
                                self.node[suc].graph,
                                self.edge[graph][suc].rhs_mapping,
                                updated_graphs[suc][1]
                            )
                        # compose homomorphisms to get p_m -> lhs_m
                        new_p_lhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_lhs[p_m_keys[0]] = lhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_lhs[p_m_key] = lhs_m_keys[i]

                        # compose homomorphisms to get p_m -> rhs_m
                        new_p_rhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_rhs[p_m_keys[0]] = rhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_rhs[p_m_key] = rhs_m_keys[i]

                        # nothing is typed by rule -- the changes can be applied right away
                        print(new_p_lhs)
                        print(new_p_rhs)
                        new_rule = Rule(
                            p_m, lhs_m, rhs_m, new_p_lhs, new_p_rhs
                        )
                        self.node[graph] = RuleNode(
                            new_rule, self.node[graph].attrs
                        )
                        self.edge[graph][suc] = RuleTyping(
                            lhs_m_suc_m, rhs_m_suc_m,
                            self.edge[graph][suc].ignore_attrs,
                            self.edge[graph][suc].attrs
                        )
                    else:
                        raise ValueError(
                            "Rewriting error: unknown type '%s' of the node '%s'!" %
                            (type(self.node[graph]), graph)
                        )
                else:
                    # complicated case
                    if isinstance(self.node[graph], GraphNode):
                        cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         self.edge[graph][suc].mapping,
                                         updated_graphs[suc][1])
                                })
                        graph_m, graph_m_graph, graph_m_sucs_m =\
                            nary_pullback(self.node[graph].graph, cospans)
                        # apply changes to the hierarchy
                        updated_graphs.update({
                            graph: (graph_m, graph_m_graph, None, None)
                        })
                        for suc, graph_m_suc in graph_m_sucs_m.items():
                            updated_homomorphisms.update({
                                (graph, suc): (
                                    graph_m_suc,
                                    self.edge[graph][suc].ignore_attrs
                                )
                            })
                    elif type(self.node[graph]) == RuleNode:
                        # propagation to lhs
                        lhs_cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                lhs_cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         self.edge[graph][suc].lhs_mapping,
                                         updated_graphs[suc][1])
                                })
                        lhs_m, lhs_m_lhs, lhs_m_sucs_m =\
                            nary_pullback(self.node[graph].rule.lhs, lhs_cospans)
                        # propagation to p

                        p_cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                p_mapping = {}
                                for node in self.node[graph].rule.p.nodes():
                                    p_mapping[node] =\
                                        self.edge[graph][suc].lhs_mapping[self.node[graph].rule.p_lhs[node]]
                                p_cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         p_mapping,
                                         updated_graphs[suc][1])
                                })
                        p_m, p_m_p, p_m_sucs_m =\
                            nary_pullback(self.node[graph].rule.p, p_cospans)
                        # propagation to rhs
                        rhs_cospans = {}
                        for suc in successors[graph]:
                            if suc in updated_graphs.keys():
                                rhs_cospans.update({
                                    suc:
                                        (updated_graphs[suc][0],
                                         self.node[suc].graph,
                                         self.edge[graph][suc].rhs_mapping,
                                         updated_graphs[suc][1])
                                })
                        rhs_m, rhs_m_rhs, rhs_m_sucs_m =\
                            nary_pullback(self.node[graph].rule.rhs, rhs_cospans)
                        # compose homomorphisms to get p_m -> lhs_m
                        new_p_lhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_lhs[p_m_keys[0]] = lhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                lhs_node = self.node[graph].rule.p_lhs[node]
                                lhs_m_keys = keys_by_value(lhs_m_lhs, lhs_node)
                                if len(lhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_lhs[p_m_key] = lhs_m_keys[i]

                        # compose homomorphisms to get p_m -> rhs_m
                        new_p_rhs = dict()
                        for node in self.node[graph].rule.p.nodes():
                            p_m_keys = keys_by_value(p_m_p, node)
                            if len(p_m_keys) == 0:
                                pass
                            elif len(p_m_keys) == 1:
                                # node stayed in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != 1:
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    new_p_rhs[p_m_keys[0]] = rhs_m_keys[0]
                            else:
                                # node was cloned in the rule
                                rhs_node = self.node[graph].rule.p_rhs[node]
                                rhs_m_keys = keys_by_value(rhs_m_rhs, rhs_node)
                                if len(rhs_m_keys) != len(p_m_keys):
                                    raise ValueError("SMTH IS WRONG!")
                                else:
                                    for i, p_m_key in enumerate(p_m_keys):
                                        new_p_rhs[p_m_key] = rhs_m_keys[i]

                        # nothing is typed by rule -- the changes can be applied right away
                        new_rule = Rule(
                            p_m, lhs_m, rhs_m, new_p_lhs, new_p_rhs
                        )
                        self.node[graph] = RuleNode(
                            new_rule, self.node[graph].attrs
                        )
                        for suc in successors[graph]:
                            self.edge[graph][suc] = RuleTyping(
                                lhs_m_sucs_m[suc], rhs_m_sucs_m[suc],
                                self.edge[graph][suc].ignore_attrs,
                                self.edge[graph][suc].attrs
                            )
                    else:
                        raise ValueError(
                            "Rewriting error: unknown type '%s' of the node '%s'!" %
                            (type(self.node[graph]), graph)
                        )

                # update step
                next_level.update(self.predecessors(graph))
                for n in self.predecessors(graph):
                    if n in successors.keys():
                        successors[n].append(graph)
                    else:
                        successors[n] = [graph]
                del successors[graph]
            current_level = next_level

        # 3. Apply changes to the hierarchy
        for graph, (graph_m, _, graph_prime, _) in updated_graphs.items():
            if graph_prime is not None:
                self.node[graph].graph = graph_prime
            else:
                self.node[graph].graph = graph_m
        for (s, t) in removed_homomorphisms:
            self.remove_edge(s, t)
        for (s, t), (mapping, ignore_attrs) in updated_homomorphisms.items():
            self.edge[s][t] = Typing(
                mapping, ignore_attrs, self.edge[s][t].attrs
            )
        return

    def to_json(self):
        """Return json representation of the hierarchy."""
        json_data = {"graphs": [], "typing": []}
        for node in self.nodes():
            json_data["graphs"].append({
                "id": node,
                "graph": graph_to_json(self.node[node].graph),
                "attrs": self.node[node].attrs
            })
        for s, t in self.edges():
            json_data["typing"].append({
                "from": s,
                "to": t,
                "mapping": self.edge[s][t].mapping,
                "ignore_attrs": self.edge[s][t].ignore_attrs,
                "attrs": self.edge[s][t].attrs
            })
        return json_data

    def load(self, filename):
        """Load the hierarchy from a file."""
        if os.path.isfile(filename):
            with open(filename, "r+") as f:
                json_data = json.loads(f.read())

                # add graphs
                for graph_data in json_data["graphs"]:
                    graph = graph_from_json(graph_data["graph"], self.directed)
                    self.add_graph(graph_data["id"], graph, graph_data["attrs"])

                # add typing
                for typing_data in json_data["typing"]:
                    self.add_typing(
                        typing_data["from"],
                        typing_data["to"],
                        typing_data["mapping"],
                        typing_data["ignore_attrs"],
                        typing_data["attrs"]
                    )
        else:
            raise ValueError("File '%s' does not exist!" % filename)

    def export(self, filename):
        """Export the hierarchy to a file."""
        with open(filename, 'w') as f:
            j_data = self.to_json()
            json.dump(j_data, f)

    def remove_attrs(self, graph_id, node, attr_dict, force=False):
        """Remove attributes of a node in a graph `graph_id`."""
        # try to remove attrs
        children = self.predecessors(graph_id)
        typing_with_attrs = set()
        for child in children:
            if self.edge[child][graph_id].ignore_attrs is False:
                typing_with_attrs.add(child)

        if len(typing_with_attrs) == 0:
            pass
            # remove_node_attrs(self.node[graph_id].graph, node, attr_dict)
        else:
            if force:
                pass
            else:
                # check no homomorphisms are broken
                pass
        return

    def get_ancestors(self, graph_id):
        """ returns the ancestors of a graph as well as the typing morphisms"""
        def _get_ancestors_aux(known_ancestors, graph_id):
            ancestors = {}
            for _, typing in self.out_edges(graph_id):
                if typing not in known_ancestors:
                    mapping = self.edge[graph_id][typing].mapping
                    typing_ancestors = _get_ancestors_aux(known_ancestors, typing)
                    ancestors[typing] = mapping
                    for (anc, typ) in typing_ancestors.items():
                        ancestors[anc] = compose_homomorphisms(typ, mapping)
                        known_ancestors.append(anc)
            return ancestors
        return _get_ancestors_aux([], graph_id)