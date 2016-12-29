#!/usr/bin/env python3

import argparse
import os
import time

import yaml
from jinja2 import Environment, FileSystemLoader

# parse command line
parser = argparse.ArgumentParser(description="Generate bind9 domain config")
parser.add_argument('--output-dir', default='config',
                    help="Where to generate config")
parser.add_argument('domain', help="The domain to generate.")
args = parser.parse_args()

# parse domains.yaml
with open('domains.yaml') as stream:
    domain_config = yaml.load(stream)
zone = args.domain

# load template engine
env = Environment(loader=FileSystemLoader(os.path.abspath('templates')))

# set default config as default values to zone config
for key, value in domain_config['default'].items():
    domain_config[zone].setdefault(key, value)

# Generate serial outside of loop so that all views have the same serial
serial = int(time.time())

for view in domain_config[zone]['views']:
    # Load templates
    conf_template = env.select_template(['%s.conf' % zone, 'default.conf'])
    zone_template = env.select_template(['%s.zone' % zone, 'default.zone'])

    # Compute dir where conf/zone file goes
    basedir = os.path.abspath(os.path.join(args.output_dir, view))
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    conf_path = os.path.join(basedir, '%s.conf' % zone)
    zone_path = os.path.join(basedir, '%s.zone' % zone)

    # Compute context for templates
    context = domain_config['default']['context'].copy()
    for key, value in domain_config[zone].get('context', {}).items():
        if isinstance(value, dict) and isinstance(context[key], dict):
            context[key].update(value)
        else:
            context[key] = value

    # Add view-specific config
    for key, value in domain_config[zone].get('%s_context' % view, {}).items():
        if isinstance(value, dict) and isinstance(context[key], dict):
            context[key].update(value)
        else:
            context[key] = value

    # Update some values that are always present
    context.update({
        'conf_path': conf_path,
        'serial': serial,
        'view': view,
        'zone': zone,
        'zone_path': zone_path,
    })

    # Actually write templates
    with open(conf_path, 'w') as stream:
        stream.write(conf_template.render(**context))
    with open(zone_path, 'w') as stream:
        stream.write(zone_template.render(**context))

    print('named-checkzone %s %s' % (zone, zone_path))
    print('rndc reload %s IN %s' % (zone, view))
