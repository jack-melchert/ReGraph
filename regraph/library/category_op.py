"""Category operations used by graph rewriting tool."""
import networkx as nx

from regraph.library.primitives import (add_node,
                                        add_edge,
                                        set_edge,
                                        add_node_attrs,
                                        get_edge,
                                        add_edge_attrs,
                                        clone_node,
                                        update_node_attrs,
                                        subtract,
                                        print_graph)
from regraph.library.utils import (keys_by_value,
                                   merge_attributes,
                                   dict_sub,
                                   is_monic,
                                   compose_homomorphisms,
                                   check_homomorphism)


def nary_pullback(b, cds):
    """Find a pullback with multiple conspans."""

    # 1. find individual pullbacks
    pullbacks = []
    for c_name, (c, d, b_d, c_d) in cds.items():
        pb = pullback(b, c, d, b_d, c_d)
        pullbacks.append((
            c_name, pb
        ))

    # 2. find pullbacks of pullbacks
    if len(pullbacks) > 1:
        c_name1, (a1, a_b1, a_c1) = pullbacks[0]
        a_c = dict([(c_name1, a_c1)])
        for i in range(1, len(pullbacks)):
            c_name2, (a2, a_b2, a_c2) = pullbacks[i]
            a1, a1_old_a1, a1_a2 = pullback(
                a1, a2, b, a_b1, a_b2
            )
            a_b1 = compose_homomorphisms(a_b1, a1_old_a1)
            # update a_c
            for c_name, old_a_c in a_c.items():
                a_c[c_name] = compose_homomorphisms(old_a_c, a1_old_a1)
            a_c[c_name2] = compose_homomorphisms(a_c2, a1_a2)

        # at the end of pullback iterations assign right a and a_b
        a_b = a_b1
        a = a1

        check_homomorphism(a, b, a_b)
        for c_name, a_c_guy in a_c.items():
            check_homomorphism(a, cds[c_name][0], a_c_guy)
        return (a, a_b, a_c)


def pullback(b, c, d, b_d, c_d):
    """Find pullback.

    Given h1 : B -> D; h2 : C -> D returns A, rh1, rh2
    with rh1 : A -> B; rh2 : A -> C and A the pullback.
    """
    if b.is_directed():
        a = nx.DiGraph()
    else:
        a = nx.Graph()

    # Check homomorphisms
    check_homomorphism(b, d, b_d)
    check_homomorphism(c, d, c_d)

    hom1 = {}
    hom2 = {}

    f = b_d
    g = c_d

    for n1 in b.nodes():
        for n2 in c.nodes():
            if f[n1] == g[n2]:
                if n1 not in a.nodes():
                    add_node(a,
                             n1,
                             merge_attributes(b.node[n1],
                                              c.node[n2],
                                              'intersection'))

                    hom1[n1] = n1
                    hom2[n1] = n2
                else:
                    i = 1
                    new_name = str(n1) + str(i)
                    while new_name in a.nodes():
                        i += 1
                        new_name = str(n1) + str(i)
                    # if n2 not in a.nodes():
                    add_node(a,
                             new_name,
                             merge_attributes(b.node[n1],
                                              c.node[n2],
                                              'intersection'))
                    hom1[new_name] = n1
                    hom2[new_name] = n2

    for n1 in a.nodes():
        for n2 in a.nodes():
            if (hom1[n1], hom1[n2]) in b.edges() or \
               ((not a.is_directed()) and (hom1[n2], hom1[n1]) in b.edges()):
                if (hom2[n1], hom2[n2]) in c.edges() or \
                   ((not a.is_directed) and (hom2[n2], hom2[n1]) in c.edges()):
                    add_edge(a, n1, n2)
                    set_edge(
                        a,
                        n1,
                        n2,
                        merge_attributes(
                            get_edge(b, hom1[n1], hom1[n2]),
                            get_edge(c, hom2[n1], hom2[n2]),
                            'intersection'))
    check_homomorphism(a, b, hom1)
    check_homomorphism(a, c, hom2)
    return (a, hom1, hom2)


def pushout(a, b, c, a_b, a_c):
    """Find pushout.
    Given h1 : A -> B; h2 : A -> C returns D, rh1, rh2
    with rh1 : B -> D; rh2 : C -> D and D the pushout.
    """

    # if h1.source_ != h2.source_:
    #     raise ValueError(
    #         "Domain of homomorphism 1 and domain of homomorphism 2 " +
    #         "don't match, can't do pushout"
    #     )
    check_homomorphism(a, b, a_b)
    check_homomorphism(a, c, a_c)

    hom1 = {}
    hom2 = {}

    d = type(b)()
    f = a_b
    g = a_c

    # add nodes to the graph
    for n in c.nodes():
        a_keys = keys_by_value(g, n)
        # addition of new nodes
        if len(a_keys) == 0:
            new_name = n
            i = 1
            while new_name in d.nodes():
                new_name = str(n) + "_" + str(i)
                i += 1
            add_node(
                d,
                new_name,
                c.node[n]
            )
            hom2[n] = n
        # addition of preserved nodes
        elif len(a_keys) == 1:
            a_key = a_keys[0]
            add_node(d, f[a_key],
                     b.node[f[a_key]])
            add_node_attrs(d, f[a_key],
                           dict_sub(c.node[g[a_key]], a.node[a_key]))
            hom1[f[a_key]] = f[a_key]
            hom2[g[a_key]] = f[a_key]
        # addition of merged nodes
        else:
            merging_nodes = []
            attrs = {}
            for a_key in a_keys:
                merging_nodes.append(f[a_key])
                attrs = merge_attributes(attrs, b.node[f[a_key]])
            new_name = "_".join([str(node) for node in merging_nodes])

            add_node(d, new_name, attrs)
            add_node_attrs(d, new_name, dict_sub(c.node[n], attrs))

            for a_key in a_keys:
                hom1[f[a_key]] = new_name
                hom2[n] = new_name

    for n in b.nodes():
        if n not in f.values():
            add_node(d, n, b.node[n])
            hom1[n] = n

    # add edges to the graph
    for (n1, n2) in c.edges():
        a_keys_1 = keys_by_value(g, n1)
        a_keys_2 = keys_by_value(g, n2)
        if len(a_keys_1) == 0 or len(a_keys_2) == 0:
            add_edge(d, hom2[n1], hom2[n2], get_edge(c, n1, n2))
        else:
            for a_key_1 in a_keys_1:
                for a_key_2 in a_keys_2:
                    if (f[a_key_1], f[a_key_2]) in b.edges():
                        if (hom2[n1], hom2[n1]) not in d.edges():
                            add_edge(d, hom2[n1], hom2[n2], get_edge(b, f[a_key_1], f[a_key_2]))
                            add_edge_attrs(d, hom2[n1],
                                           hom2[n2],
                                           dict_sub(get_edge(c, n1, n2),
                                                    get_edge(a, a_key_1, a_key_2)))
                        else:
                            add_edge_attrs(d, hom2[n1],
                                           hom2[n2],
                                           get_edge(b, f[a_key_1], f[a_key_2]))
                            add_edge_attrs(d, hom2[n1],
                                           hom2[n2],
                                           dict_sub(get_edge(c, n1, n2),
                                                    get_edge(a, a_key_1, a_key_2)))
                    elif (hom2[n1], hom2[n2]) not in d.edges():
                        add_edge(d, hom2[n1], hom2[n2], get_edge(c, n1, n2))

    for (n1, n2) in b.edges():
        a_keys_1 = keys_by_value(f, n1)
        a_keys_2 = keys_by_value(f, n2)
        if len(a_keys_1) == 0 or len(a_keys_2) == 0:
            add_edge(d, hom1[n1], hom1[n2], get_edge(b, n1, n2))
        elif (hom1[n1], hom1[n2]) not in d.edges():
            add_edge(d, hom1[n1], hom1[n2], get_edge(b, n1, n2))

    check_homomorphism(b, d, hom1)
    check_homomorphism(c, d, hom2)
    return (d, hom1, hom2)


def pullback_complement(a, b, d, a_b, b_d):
    """Find pullback complement.

    Given h1 : A -> B; h2 : B -> D returns C, rh1, rh2
    with rh1 : A -> C; rh2 : C -> D and C the pullback_complement.
    Doesn't work if h2 is not a matching
    """

    check_homomorphism(a, b, a_b)
    check_homomorphism(b, d, b_d)

    if not is_monic(b_d):
        raise ValueError(
            "Second homomorphism is not monic, cannot find final pullback complement!"
        )

    c = type(b)()
    f = a_b
    g = b_d

    hom1 = {}
    hom2 = {}

    # a_d = compose_homomorphisms(g, f)
    d_m_b = subtract(d, b, g)

    for n in a.nodes():
        if g[f[n]] not in c.nodes():
            add_node(c, g[f[n]],
                     dict_sub(d.node[g[f[n]]], b.node[f[n]]))
            add_node_attrs(c, g[f[n]], a.node[n])
            hom1[n] = g[f[n]]
            hom2[g[f[n]]] = g[f[n]]
        else:
            new_name = clone_node(c, g[f[n]])
            update_node_attrs(
                c, new_name,
                dict_sub(d.node[g[f[n]]], b.node[f[n]])
            )
            add_node_attrs(c, new_name, a.node[n])
            hom1[n] = new_name
            hom2[new_name] = g[f[n]]

    for n in d_m_b.nodes():
        is_in_a = False
        for n0 in a.nodes():
            if g[f[n0]] == n:
                is_in_a = True
                break
        if not is_in_a:
            add_node(c, n, d_m_b.node[n])
            hom2[n] = n

    # Add edges from preserved part
    for (n1, n2) in a.edges():
        attrs = dict_sub(get_edge(d, g[f[n1]], g[f[n2]]), get_edge(b, f[n1], f[n2]))
        add_edge(c, hom1[n1], hom1[n2], attrs)
        add_edge_attrs(c, hom1[n1], hom1[n2], get_edge(a, n1, n2))

    # Add remaining edges from D
    for (n1, n2) in d.edges():
        b_key_1 = keys_by_value(g, n1)
        b_key_2 = keys_by_value(g, n2)
        if len(b_key_1) == 0 or len(b_key_2) == 0:
            add_edge(c, n1, n2, get_edge(d, n1, n2))
        else:
            if (b_key_1[0], b_key_2[0]) not in b.edges():
                c_keys_1 = keys_by_value(hom2, n1)
                c_keys_2 = keys_by_value(hom2, n2)
                for c1 in c_keys_1:
                    for c2 in c_keys_2:
                        if (c1, c2) not in c.edges():
                            add_edge(c, c1, c2, get_edge(d, n1, n2))

    check_homomorphism(a, c, hom1)
    check_homomorphism(c, d, hom2)

    return (c, hom1, hom2)
