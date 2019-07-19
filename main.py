#!/usr/bin/env python
#  Copyright 2019 Manuel Olguín Muñoz <manuel@olguin.se><molguin@kth.se>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import enum
import ipaddress
import signal
from multiprocessing import Event
from typing import List, Optional

import click

from proxy import BaseDelayProxy, ExponentialDelayProxy


class INetAddress(click.ParamType):
    class TYPE(enum.IntEnum):
        TO = 0
        FROM = 1

    def __init__(self, to_or_from: Optional[TYPE] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = {
            INetAddress.TYPE.TO  : 'HOST_ADDRESS:HOST_PORT',
            INetAddress.TYPE.FROM: 'BIND_ADDRESS:BIND_PORT'
        }.get(to_or_from, 'ADDRESS:PORT')

    def convert(self, value, param, ctx):
        try:
            [ip, port] = value.split(':')
            ipaddress.ip_address(ip)
            port = int(port)
            assert port < 65535
        except Exception:
            self.fail(f'{value} is not a valid IPv4 or IPv6 address.',
                      param, ctx)
        return ip, port


@click.command()
@click.option('-v', '--verbose',
              count=True, type=int, default=0,
              help='Logging verbosity.')
@click.option('-p', '--proxy',
              required=True,
              type=click.Tuple([INetAddress(INetAddress.TYPE.FROM),
                                INetAddress(INetAddress.TYPE.TO)]),
              nargs=2,
              multiple=True,
              help='\
Hosts to relay packets between, can be provided multiple times to specify \
multiple relays. The application will bind and listen for an incoming \
connection on BIND_ADDRESS:BIND_PORT and relay all data coming from it to \
HOST_ADDRESS:HOST_PORT.'
              )
def main(verbose, proxy):
    proxies: List[BaseDelayProxy] = list()

    def __sig_handler(*args, **kwargs):
        for p in proxies:
            p.stop()
        exit(0)

    signal.signal(signal.SIGINT, __sig_handler)

    for addr_a, addr_b in proxy:
        print(f'Setting up relay from {addr_a} to {addr_b}...')
        listen_host, listen_port = addr_a
        connect_host, connect_port = addr_b
        proxies.append(ExponentialDelayProxy(
            scale=0.1,
            listen_host=listen_host,
            listen_port=listen_port,
            connect_host=connect_host,
            connect_port=connect_port))

    for p in proxies:
        p.start()

    Event().wait()  # wait forever


if __name__ == '__main__':
    main()
