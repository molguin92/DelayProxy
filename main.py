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
import toml

from distributions import ConstantDistribution, PseudoNormalDistribution, \
    ExponentialDistribution
from proxy import DelayProxy


class TOMLFile(click.File):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def convert(self, value, param, ctx):
        return toml.load(super().convert(value, param, ctx))


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


def print_help(ctx, param, value):
    click.echo(ctx.get_help())
    ctx.exit()


@click.group()
@click.option('-v', '--verbose',
              count=True, type=int, default=0,
              help='Logging verbosity.')
def cli(verbose):
    # TODO: logging
    pass


@cli.group(help='Start a single proxy from the CLI.')
@click.option('-c', '--chunk_size', type=int, default=4096, required=False,
              show_default=True,
              help='Read/write chunk size for the TCP proxy in bytes.')
@click.argument('bind_addr', type=INetAddress(INetAddress.TYPE.FROM))
@click.argument('connect_addr', type=INetAddress(INetAddress.TYPE.TO))
@click.pass_context
def proxy(ctx, chunk_size, bind_addr, connect_addr):
    print(f'Starting relay: {bind_addr} -> {connect_addr}')

    lhost, lport = bind_addr
    chost, cport = connect_addr
    ctx.obj = DelayProxy(
        listen_host=lhost,
        listen_port=lport,
        connect_host=chost,
        connect_port=cport,
        chunk_size=chunk_size
    )


@proxy.command(help='Proxy with a constant delay between chunks of data.')
@click.option('-c', '--constant', type=float, default=0.0, required=False,
              show_default=True,
              help='Constant delay, in seconds, to apply '
                   'between chunks of data.')
@click.pass_context
def constant_delay(ctx, constant):
    ctx.ensure_object(DelayProxy)
    ctx.obj.set_distribution(ConstantDistribution(constant=constant))
    single_run(ctx.obj)


@proxy.command(help='Proxy with normally distributed delays '
                    'between chunks of data.')
@click.argument('mean', type=float)
@click.argument('std_dev', type=float)
@click.pass_context
def gaussian_delay(ctx, mean, std_dev):
    ctx.ensure_object(DelayProxy)
    ctx.obj.set_distribution(PseudoNormalDistribution(mean, std_dev))
    single_run(ctx.obj)


@proxy.command(help='Proxy with exponentially distributed delays '
                    'between chunks of data.')
@click.argument('scale', type=float)
@click.pass_context
def exponential_delay(ctx, scale):
    ctx.ensure_object(DelayProxy)
    ctx.obj.set_distribution(ExponentialDistribution(scale))
    single_run(ctx.obj)


def single_run(proxy: DelayProxy):
    def __sig_handler(*args, **kwargs):
        proxy.stop()
        exit(0)

    signal.signal(signal.SIGINT, __sig_handler)
    proxy.start()

    Event().wait()  # wait forever


@cli.command()
@click.argument('config', type=TOMLFile())
def from_file(config):
    pass


if __name__ == '__main__':
    cli()
