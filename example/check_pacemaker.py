#!/usr/bin/python

# -*- coding: utf-8 -*-
"""
Xymon Extention Module for monitoring Pacemaker servers
Copyright (C) 2017 Davide Madrisan <davide.madrisan.gmail.com>
"""

from __future__ import print_function

__author__ = "Davide Madrisan"
__copyright__ = "Copyright 2017 Davide Madrisan"
__license__ = "GPL-3.0"
__version__ = "3"
__email__ = "davide.madrisan.gmail.com"
__status__ = "Beta"

# Import python libs
from pcs import (
    status,
    utils
)
from xml.dom.minidom import parseString
from pcs.lib import pacemaker as lib_pacemaker
import getopt
import os
import sys
import pyxymon as pymon

__check_version__ = (os.path.basename(__file__), __version__)

def die(message, exitcode=1):
    """Print an error message and exit with 'exitcode'"""
    progname = sys.argv[0]
    print('{0}: error: {1}'.format(progname, message), file=sys.stderr)
    sys.exit(exitcode)

def usage():
    """Print the usage message"""
    progname = sys.argv[0]
    for line in [
        'Xymon Extention Module for monitoring Pacemaker servers',
        '{0} <{1}>'.format(__copyright__, __email__),
        'Usage:',
        '\t{0} -t <test-name> [-d] [-r <host>:<resource-group>]'.format(progname),
        '\t{0} --help'.format(progname),
        'Example:',
        '\tsudo {0} -t rhcluster -d -r pcsnode1:rblock1 -r pcsnode1:rblock2'.format(
            progname)
    ]:
        print(line)

def get_cluster_name():
    """
    Return the cluster name.
    Example of output: 'mycluster'
    """
    return utils.getClusterName()

def cluster_nodes():
    """
    Return the list of cluster nodes.
    Example of output: [u'cluster-node1', u'cluster-node2']
    """
    info_dom = utils.getClusterState()
    nodes = info_dom.getElementsByTagName('nodes')
    if nodes.length == 0:
        raise CommandExecutionError('No nodes section found')
    all_nodes = nodes[0].getElementsByTagName('node')

    return list(node.getAttribute('name') for node in all_nodes)

def cluster_local_node_status():
    """
    Return the status of the local cluster member.
    Example of output:
        {
            u'resources_running': 10,
            u'shutdown': False,
            u'name': 'cluster-node1',
            u'standby': False,
            u'standby_onfail': False,
            u'expected_up': True,
            u'is_dc': True,
            u'maintenance': False,
            u'online': True,
            u'offline': False,
            u'type': 'member',
            u'id': '1',
            u'pending': False,
            u'unclean': False
        }
    """
    try:
        node_status = lib_pacemaker.get_local_node_status(
            utils.cmd_runner()
        )
    except LibraryError as exc:
        raise RuntimeError('Unable to get node status: {0}'.format(
            '\n'.join([item.message for item in exc.args]))
        )
    return node_status

def cluster_resources():
    """
    Return the status of the local resources.
    Example of output:
        {
            u'data2_fs': {
                'node': u'cluster-node2',
                'resource_agent': u'ocf::heartbeat:Filesystem',
                'role': u'Started'
            },
            ...
            u'data1vg': {
                'node': u'frsopslapp051-node1',
                'resource_agent': u'ocf::heartbeat:LVM',
                'role': u'Started'
            },
            ...
        }
    """
    info_dom = utils.getClusterState()
    resources = info_dom.getElementsByTagName('resources')
    if resources.length == 0:
        raise RuntimeError('No resources section found')

    def _pack_data(resource):
        nodes = resource.getElementsByTagName('node')
        node = list(node.getAttribute('name')
                   for node in nodes if nodes.length > 0)
        resource_agent = resource.getAttribute('resource_agent')
        resource_id = resource.getAttribute('id')
        role = resource.getAttribute('role')
        return (resource_id, dict(
                resource_agent = resource_agent,
                role = role,
                node = node[0] if len(node) == 1 else node))

    return dict(_pack_data(resource)
        for resource in resources[0].getElementsByTagName('resource'))

def cluster_resource_groups():
    """
    Return the list of resource groups and resources.
    Example of output:
        {
            'resource-group1': ['resource1', 'resource2'],
            ...
        }
    """
    groups = list()
    group_xpath = '//group'
    group_xml = utils.get_cib_xpath(group_xpath)
    # If no groups exist, we silently return
    if not group_xml:
        return groups

    element = parseString(group_xml).documentElement
    # If there is more than one group returned it's wrapped in an xpath-query
    # element
    elements = (element.getElementsByTagName('group')
        if element.tagName == 'xpath-query' else list(element))
    return dict((e.getAttribute("id"),
                 list(e.getAttribute("id") for e in
                     e.getElementsByTagName("primitive"))) for e in elements)

def check_resource_groups_status(
    resource_group_required, node_resources, resource_groups):
    """
    Check if the resources belongs to the 'resource_group_required'.
    Note: 'resource_group_required' is a vector containing the names of all
    the resource groups that must be active on the cluster node.
    """
    if not resource_group_required:
        return True

    groups = list(group for group in resource_groups
        for resource in node_resources if resource in resource_groups[group])

    # Check if this matches the value set in the xymon config file
    return set(resource_group_required) <= set(groups)

def get_cluster_infos(resource_groups_cfg_map):
    """
    Return a dictionary containg all the cluster informations necessary
    to the monitoring logic.
    """
    cl_local_node_status = cluster_local_node_status()
    _get_local_node_attr = \
        lambda attr: cl_local_node_status.get(attr, 'Unknown')

    node_name = _get_local_node_attr('name')
    node_status = 'online' if _get_local_node_attr('online') else 'offline'

    # get the list of resources configured on this cluster node
    all_resources = cluster_resources()
    node_resources = dict((k, v)
        for k,v in all_resources.items() if v.get('node') == node_name)
    # get the number of running resources on this cluster node
    resources_running = _get_local_node_attr('resources_running')

    # get the list of resource groups required to be running on
    # 'node_name', according to the xymon configuration file
    resource_group_required = (
        resource_groups_cfg_map.get(node_name, None))
    resource_groups = cluster_resource_groups()
    resource_groups_status = check_resource_groups_status(
        resource_group_required, node_resources, resource_groups)

    return dict(
        cluster_name = get_cluster_name(),
        node_name = node_name,
        node_resource_groups_match_cfg = resource_groups_status,
        node_resources = node_resources,
        node_status = node_status,
        resources_running = resources_running
    )

def check_cluster_status(test_name, resource_groups_cfg_map, check_daemons):
    """
    Check the status of the pacemaker cluster, create and sent the message
    to the xymon server.
    """
    xymon = pymon.XymonClient(test_name)
    cluster_infos = get_cluster_infos(resource_groups_cfg_map)
    cluster_name = cluster_infos['cluster_name']
    node_name = cluster_infos['node_name']
    resources_match_cfg = cluster_infos['node_resource_groups_match_cfg']
    node_status = (cluster_infos['node_status'] if resources_match_cfg
        else '{0} (resources have switched)'.format(
            cluster_infos['node_status']))
    # message - title
    xymon.title(
        'Pacemaker cluster "{0}"'.format(cluster_name))

    # message - cluster node status
    node_color = (pymon.STATUS_OK if node_status == 'online'
        else pymon.STATUS_CRITICAL)
    xymon.section(
        'Node Status',
        '{0} - {1} {2}'.format(node_name, node_status, node_color))
    xymon.color = node_color

    # message - cluster nodes
    nodes = sorted(cluster_nodes())
    xymon.section('Cluster Nodes', ', '.join(nodes))

    # message - resources
    resources_summary = (
        '{c[resources_running]} resources running:\n\n'.format(
            c=cluster_infos))
    resources_color = lambda v: \
        pymon.STATUS_OK if v.get('role') == 'Started' else pymon.STATUS_CRITICAL
    resources_list_with_status = '\n'.join(' {0} {1:<22} {2}'.format(
        resources_color(v), k, v.get('resource_agent'))
             for k,v in cluster_infos['node_resources'].items())
    xymon.section('Cluster Resources', '{0}{1}'.format(
        resources_summary, resources_list_with_status))
    if not all([item.split()[0] == pymon.STATUS_OK \
                for item in resources_list_with_status.splitlines()]):
        xymon.color = pymon.STATUS_CRITICAL

    # message - daemons status
    if check_daemons:
        cluster_services = ['corosync', 'pacemaker', 'pcsd']
        service_status = lambda service: ' {0} service {1:<14} {2}\n'.format(
            *((pymon.STATUS_OK, service, 'active')
                if status.is_service_running(service)
                else (pymon.STATUS_CRITICAL, service, 'inactive')))
        xymon.section(
            'Daemon Status',\
            ''.join(service_status(service) for service in cluster_services))
        if not all(status.is_service_running(service)
                   for service in cluster_services):
            xymon.color = pymon.STATUS_CRITICAL

    # message - footer
    xymon.footer(__check_version__)

    xymon.send()

if __name__ == '__main__':
    if os.geteuid() != 0:
        raise RuntimeError('This script must be run as root')

    test_name = None
    check_daemons = False
    resource_groups_map = dict()

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'dr:t:h',
                     ["daemons", "resource=", "test=", "help"])
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        elif o in ('-d', '--daemons'):
            check_daemons = True
        elif o in ('-r', '--resource'):
            service, node = a.split(':')
            resource_groups_map.setdefault(service,[]).append(node)
        elif o in ('-t', '--test'):
            test_name = a
        else:
            die('Unhandled command line option: {0}'.format(o))

    if not test_name:
        usage()
        sys.exit(1)

    check_cluster_status(test_name, resource_groups_map, check_daemons)
    sys.exit(0)
