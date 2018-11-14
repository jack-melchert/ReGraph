import networkx as nx

from regraph import Rule
from regraph import keys_by_value
from regraph import RuleError
from regraph.networkx.category_utils import check_homomorphism
import regraph.primitives as prim


class TestRule(object):
    """Class for testing `regraph.rules` module."""

    def __init__(self):
        """Initialize test."""
        # Define the left hand side of the rule
        self.pattern = nx.DiGraph()
        self.pattern.add_node(1)
        self.pattern.add_node(2)
        self.pattern.add_node(3)
        prim.add_node(self.pattern, 4, {'a': 1})

        self.pattern.add_edges_from([
            (1, 2),
            (3, 2),
            (4, 1)
        ])
        prim.add_edge(self.pattern, 2, 3, {'a': {1}})

        # Define preserved part of the rule
        self.p = nx.DiGraph()
        self.p.add_node('a')
        self.p.add_node('b')
        self.p.add_node('c')
        prim.add_node(self.p, 'd', {'a': 1})

        self.p.add_edges_from([
            ('a', 'b'),
            ('d', 'a')
        ])
        prim.add_edge(self.p, 'b', 'c', {'a': {1}})

        # Define the right hand side of the rule
        self.rhs = nx.DiGraph()
        self.rhs.add_node('x')
        self.rhs.add_node('y')
        self.rhs.add_node('z')
        # self.rhs.add_node('s', {'a': 1})
        prim.add_node(self.rhs, 's', {'a': 1})
        self.rhs.add_node('t')

        self.rhs.add_edges_from([
            ('x', 'y'),
            # ('y', 'z', {'a': {1}}),
            ('s', 'x'),
            ('t', 'y')
        ])
        prim.add_edge(self.rhs, 'y', 'z', {'a': {1}})

        # Define mappings
        self.p_lhs = {'a': 1, 'b': 2, 'c': 3, 'd': 4}
        self.p_rhs = {'a': 'x', 'b': 'y', 'c': 'z', 'd': 's'}
        return

    def test_inject_remove_node(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [1, 2, 3])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        rule.inject_remove_node(2)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert(2 in rule.lhs.nodes())
        assert(2 not in rule.p.nodes())
        assert(2 not in rule.rhs.nodes())

    def test_inject_clone_node(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [1, 2, 3])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        new_p_node, new_rhs_node = rule.inject_clone_node(2)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert(new_p_node in rule.p.nodes())
        assert(new_rhs_node in rule.rhs.nodes())
        assert(rule.p_rhs[new_p_node] == new_rhs_node)
        assert((1, new_p_node) in rule.p.edges())
        assert((3, new_p_node) in rule.p.edges())
        assert((1, new_rhs_node) in rule.rhs.edges())
        assert((3, new_rhs_node) in rule.rhs.edges())
        new_p_node, new_rhs_node = rule.inject_clone_node(2)
        assert(len(keys_by_value(rule.p_lhs, 2)) == 3)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        rule.inject_remove_node(3)
        try:
            rule.inject_clone_node(3)
            raise ValueError("Cloning of removed node was not caught")
        except:
            pass

    def test_inject_remove_edge(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [1, 2, 3])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        rule.inject_remove_edge(3, 2)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert((3, 2) not in rule.p.nodes())
        new_name, _ = rule.inject_clone_node(2)
        rule.inject_remove_edge(1, new_name)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert((1, new_name) not in rule.p.edges())
        assert((1, 2) in rule.p.edges())

    def test_inject_remove_node_attrs(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(
            pattern,
            [1, (2, {"a2": {True}}), (3, {"a3": {False}})])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        rule.inject_remove_node_attrs(3, {"a3": {False}})
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert("a3" not in rule.p.nodes[3])
        assert("a3" in rule.lhs.nodes[3])
        new_p_node, new_rhs_node = rule.inject_clone_node(2)
        rule.inject_remove_node_attrs(new_p_node, {"a2": {True}})
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert("a2" not in rule.p.nodes[new_p_node])
        assert("a2" in rule.p.nodes[2])
        assert("a2" not in rule.rhs.nodes[new_rhs_node])
        assert("a2" in rule.rhs.nodes[2])

    def test_inject_remove_edge_attrs(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(
            pattern,
            [1, 2, 3])
        prim.add_edges_from(
            pattern,
            [(1, 2, {"a12": {True}}), (3, 2, {"a32": {True}})])
        rule = Rule.from_transform(pattern)
        rule.inject_remove_edge_attrs(1, 2, {"a12": {True}})
        assert("a12" not in rule.p.edges[1, 2])
        new_p_node, new_rhs_node = rule.inject_clone_node(2)
        assert("a12" not in rule.p.edges[1, new_p_node])
        rule.inject_remove_edge_attrs(3, new_p_node, {"a32": {True}})
        assert("a32" in rule.p.edges[3, 2])
        assert("a32" not in rule.p.edges[3, new_p_node])
        assert("a32" in rule.rhs.edges[3, rule.p_rhs[2]])
        assert("a32" not in rule.rhs.edges[3, new_rhs_node])

    def test_inject_add_node(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [1, 2, 3])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        try:
            rule.inject_add_node(3)
            raise ValueError("Node duplication was not caught")
        except RuleError:
            pass
        rule.inject_add_node(4)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert(4 in rule.rhs.nodes() and
               4 not in rule.lhs.nodes() and
               4 not in rule.p.nodes())

    def test_inject_add_edge(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [1, 2, 3])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        rule.inject_add_node(4)
        rule.inject_add_edge(1, 4)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert((1, 4) in rule.rhs.edges())
        merge_node = rule.inject_merge_nodes([1, 2])
        rule.inject_add_edge(merge_node, 3)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert((merge_node, 3) in rule.rhs.edges())
        new_p_node, new_rhs_node = rule.inject_clone_node(2)
        rule.inject_add_edge(new_p_node, merge_node)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert((new_rhs_node, merge_node) in rule.rhs.edges())

    def test_inject_merge_nodes(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [1, 2, 3])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        new_name = rule.inject_merge_nodes([1, 2])
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert((new_name, new_name) in rule.rhs.edges())
        assert((3, new_name) in rule.rhs.edges())
        new_p_name, new_rhs_name = rule.inject_clone_node(2)
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        new_name = rule.inject_merge_nodes([2, 3])
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)
        assert(new_p_name in rule.rhs.nodes())

    def test_inject_add_node_attrs(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [1, 2, 3])
        prim.add_edges_from(pattern, [(1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        clone_name_p, clone_name_rhs = rule.inject_clone_node(2)
        rule.inject_add_node(4)
        merge = rule.inject_merge_nodes([1, 3])
        rule.inject_add_node_attrs(2, {"a": {True}})
        assert("a" in rule.rhs.nodes[2])
        assert("a" in rule.rhs.nodes[clone_name_rhs])
        rule.inject_add_node_attrs(clone_name_p, {"b": {True}})
        assert("b" in rule.rhs.nodes[clone_name_rhs])
        assert("b" not in rule.rhs.nodes[2])
        rule.inject_add_node_attrs(4, {"c": {True}})
        assert("c" in rule.rhs.nodes[4])
        rule.inject_add_node_attrs(merge, {"d": {True}})
        assert("d" in rule.rhs.nodes[merge])
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)

    def test_inject_add_edge_attrs(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(pattern, [0, 1, 2, 3])
        prim.add_edges_from(pattern, [(0, 1), (0, 2), (1, 2), (3, 2)])
        rule = Rule.from_transform(pattern)
        clone_name_p, clone_name_rhs = rule.inject_clone_node(2)
        rule.inject_add_node(4)
        rule.inject_add_edge(4, 3)
        merge = rule.inject_merge_nodes([1, 3])

        rule.inject_add_edge_attrs(0, 1, {"a": {True}})
        assert("a" in rule.rhs.edges[0, merge])
        rule.inject_add_edge_attrs(0, clone_name_p, {"b": {True}})
        assert("b" in rule.rhs.edges[0, clone_name_rhs])
        rule.inject_add_edge_attrs(merge, clone_name_p, {"c": {True}})
        assert("c" in rule.rhs.edges[merge, clone_name_rhs])
        assert("c" not in rule.rhs.edges[merge, 2])
        rule.inject_add_edge_attrs(4, merge, {"d": {True}})
        assert("d" in rule.rhs.edges[4, merge])
        check_homomorphism(rule.p, rule.lhs, rule.p_lhs)
        check_homomorphism(rule.p, rule.rhs, rule.p_rhs)

    def test_inject_update_node_attrs(self):
        pass

    def test_inject_update_edge_attrs(self):
        pass

    def test_from_script(self):
        commands = "clone 2 as '21'.\nadd_node 'a' {'a': 1}.\ndelete_node 3."
        rule = Rule.from_transform(self.pattern, commands=commands)
        assert('a' in rule.rhs.nodes())
        assert('21' in rule.rhs.nodes())
        assert(3 not in rule.rhs.nodes())

    def test_component_getters(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(
            pattern,
            [(1, {"a1": {1}}), (2, {"a2": {2}}), (3, {"a3": {3}})]
        )
        prim.add_edges_from(
            pattern,
            [
                (1, 2, {"a12": {12}}),
                (2, 3),
                (3, 2, {"a32": {32}})
            ]
        )

        rule = Rule.from_transform(pattern)
        rule.inject_remove_node(1)
        rule.inject_remove_edge(2, 3)
        new_p_name, new_rhs_name = rule.inject_clone_node(2)
        rule.inject_remove_node_attrs(3, {"a3": {3}})
        rule.inject_remove_edge_attrs(3, 2, {"a32": {32}})
        rule.inject_add_node_attrs(3, {"a3": {100}})
        rule.inject_add_node(4)
        rule.inject_add_edge(4, new_p_name)

        assert(rule.removed_nodes() == {1})
        assert(rule.removed_edges() == {(2, 3), (new_p_name, 3)})
        assert(len(rule.cloned_nodes()) == 1 and
               2 in rule.cloned_nodes().keys())
        assert(len(rule.removed_node_attrs()) == 1 and
               3 in rule.removed_node_attrs()[3]["a3"])
        assert(len(rule.removed_edge_attrs()) == 1 and
               32 in rule.removed_edge_attrs()[(3, 2)]["a32"])

        assert(rule.added_nodes() == {4})
        assert(rule.added_edges() == {(4, "21")})
        # rule.merged_nodes()
        # rule.added_edge_attrs()
        assert(len(rule.added_node_attrs()) == 1 and
               100 in rule.added_node_attrs()[3]["a3"])
        assert(rule.is_restrictive() and rule.is_relaxing())

    def test_from_commands(self):
        pattern = nx.DiGraph()
        prim.add_nodes_from(
            pattern,
            [(1, {'state': 'p'}),
             (2, {'name': 'BND'}),
             3,
             4]
        )
        prim.add_edges_from(
            pattern,
            [(1, 2, {'s': 'p'}),
             (3, 2, {'s': 'u'}),
             (3, 4)]
        )

        p = nx.DiGraph()
        prim.add_nodes_from(
            p,
            [(1, {'state': 'p'}), ("1_clone", {'state': 'p'}), (2, {'name': 'BND'}), 3, 4])
        prim.add_edges_from(
            p, [(1, 2), ('1_clone', 2), (3, 4)])

        rhs = nx.DiGraph()
        prim.add_nodes_from(
            rhs,
            [(1, {'state': 'p'}), ("1_clone", {'state': 'p'}), (2, {'name': 'BND'}), 3, 4, 5])

        prim.add_edges_from(
            rhs, [(1, 2, {'s': 'u'}), ('1_clone', 2), (2, 4), (3, 4), (5, 3)])

        p_lhs = {1: 1, '1_clone': 1, 2: 2, 3: 3, 4: 4}
        p_rhs = {1: 1, '1_clone': '1_clone', 2: 2, 3: 3, 4: 4}
        rule1 = Rule(p, pattern, rhs, p_lhs, p_rhs)

        commands = "clone 1.\n" +\
            "delete_edge 3 2.\n" +\
            "add_node 5.\n" +\
            "add_edge 2 4.\n" +\
            "add_edge 5 3."

        rule2 = Rule.from_transform(pattern, commands)
        assert((5, 3) in rule2.rhs.edges())
        assert(5 in rule2.rhs.nodes() and 5 not in rule2.p.nodes())
        assert((2, 4) in rule2.rhs.edges())
