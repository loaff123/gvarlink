"""Offline inspect, verify and original-data demo commands."""
import argparse
import json
import subprocess
import sys
from .errors import GVarLinkError
from .format import inspect
from .adapter import load_many


def main(argv=None):
    parser=argparse.ArgumentParser(prog='gvarlink',description='Validate declared-source numeric artifacts. Checksums are not authentication.')
    commands=parser.add_subparsers(dest='command',required=True)
    one=commands.add_parser('inspect',help='fully verify and show metadata');one.add_argument('path')
    many=commands.add_parser('verify',help='validate and reconcile files in a shared gvar context');many.add_argument('paths',nargs='+')
    demo=commands.add_parser('demo',help='run original synthetic two-writer/one-reader example');demo.add_argument('directory')
    args=parser.parse_args(argv)
    try:
        if args.command=='inspect':result=inspect(args.path)
        elif args.command=='verify':
            context,arrays=load_many(args.paths)
            result=dict(integrity='verified',files=len(arrays),sources=len(context.sources),
                        coordinates=sum(s.size for s in context.sources),
                        warning='UUIDs and basis declarations are not authenticated scientific facts')
        else:
            from .demo import run_demo
            result=run_demo(args.directory)
        print(json.dumps(result,sort_keys=True,allow_nan=False))
        return 0
    except (GVarLinkError,OSError,subprocess.SubprocessError) as error:
        print(f'gvarlink: error: {error}',file=sys.stderr)
        return 2
