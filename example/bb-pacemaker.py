#!/usr/bin/python

# -*- coding: utf-8 -*-
"""
Module Xymon for monitoring a Pacemaker cluster.
Copyright (C) 2017 Davide Madrisan <davide.madrisan.gmail.com>
"""

# Import python libs
from pcs import (
    status,
    utils,
)
from pcs.lib import pacemaker as lib_pacemaker
import os
import sys
# Import the pyxymon library
import pyxymon as pymon

__check_name__ = 'pacemaker'
__check_version__ = (os.path.basename(__file__), '1')

def cluster_name():
    """Return the cluster name."""
    return utils.getClusterName()

def cluster_local_node_status():
    """Return the status of the local cluster member."""
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
    """Return the status of the local resources."""
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

def check_cluster_status():
    """
    Check the status of the pacemaker cluster, create and sent the message
    to the xymon server.
    """
    xymon = pymon.XymonClient(__check_name__)

    cl_local_node_status = cluster_local_node_status()
    _get_attr = lambda attr: cl_local_node_status.get(attr, 'Unknown')
    node_name = _get_attr('name')

    color, status_message = ((xymon.msg.OK, 'online')
        if _get_attr('online') else (xymon.msg.CRITICAL, 'offline'))
    node_status = '{0} {1}'.format(status_message, color)
    xymon.msg.color(color)
    all_resources = cluster_resources()
    node_resources = dict((k, v)
        for k,v in all_resources.items() if v.get('node') == node_name)
    resources_running = _get_attr('resources_running')

    cluster_infos = {
        'name': cluster_name(),
        'node_name': node_name,
        'node_status': node_status,
        'resources_running': resources_running,
    }
    cluster_services = ['corosync', 'pacemaker', 'pcsd']

    # message - title
    xymon.msg.title(
        'Pacemaker cluster "{c[name]}"'.format(c=cluster_infos))

    # message - cluster node status
    xymon.msg.section(
        'Node Status',\
        '{c[node_name]} - {c[node_status]}'.format(c=cluster_infos))

    # message - resources
    resources_summary = (
        '{c[resources_running]} resources running:\n\n'.format(
            c=cluster_infos))
    resources_color = lambda v: \
        xymon.msg.OK if v.get('role') == 'Started' else xymon.msg.CRITICAL
    resources_list_with_status = '\n'.join(' {0} {1:<22} {2}'.format(
        resources_color(v), k, v.get('resource_agent'))
             for k,v in node_resources.items())
    xymon.msg.section('Cluster Resources', '{0}{1}'.format(
        resources_summary, resources_list_with_status))
    if not all([item.split()[0] == xymon.msg.OK \
                for item in resources_list_with_status.splitlines()]):
        xymon.msg.color(xymon.msg.CRITICAL)

    # message - daemons status
    service_status = lambda service: ' {0} service {1:<14} {2}\n'.format(
        *((xymon.msg.OK, service, 'active')
            if status.is_service_running(service)
            else (xymon.msg.CRITICAL, service, 'inactive')))
    xymon.msg.section(
        'Daemon Status',\
        ''.join(service_status(service) for service in cluster_services))

    if not all(status.is_service_running(service)
                   for service in cluster_services):
        xymon.msg.color(xymon.msg.CRITICAL)

    # message - footer
    xymon.msg.footer(__check_version__)

    xymon.send()

def main():
    """Main function"""
    check_cluster_status()

if __name__ == '__main__':
    if os.geteuid() != 0:
        raise RuntimeError('This script must be run as root')
    main()
    sys.exit(0)
