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

import multiprocessing
import signal
import socket
from typing import Optional

from logzero import logger

from distributions import Distribution


def noop(*args, **kwargs):
    pass


class SimplexRelay(multiprocessing.Process):
    def __init__(self,
                 conn_a: socket.SocketType,
                 conn_b: socket.SocketType,
                 delay_dist: Distribution,
                 chunk_size: int = 512):
        super().__init__(daemon=True)
        self.conn_a = conn_a
        self.conn_b = conn_b
        self.delay_dist = delay_dist
        self.chunk_size = chunk_size

        self.shutdown_signal = multiprocessing.Event()
        self.shutdown_signal.clear()

    def run(self) -> None:
        signal.signal(signal.SIGINT, noop)  # remove signal handlers

        from_addr = self.conn_a.getpeername()
        to_addr = self.conn_b.getpeername()
        logger.info('Relaying data from '
                    '{}:{} to {}:{}'.format(*from_addr, *to_addr))
        while not self.shutdown_signal.is_set():
            try:
                data = self.conn_a.recv(self.chunk_size)
                self.shutdown_signal.wait(timeout=self.delay_dist.sample())
                # time.sleep(self.delay_dist.sample())
                self.conn_b.sendall(data)
            except socket.error as e:
                logger.warning(e)
                break
            except Exception as e:
                logger.exception(e)
                break
        logger.info('Done relaying from '
                    '{}:{} to {}:{}'.format(*from_addr, *to_addr))

    def stop(self) -> None:
        self.shutdown_signal.set()


class DuplexRelay(multiprocessing.Process):

    def __init__(self,
                 listen_host: str,
                 listen_port: int,
                 connect_host: str,
                 connect_port: int,
                 delay_dist: Optional[Distribution] = None,
                 chunk_size: int = 512):
        super().__init__()
        logger.info(f'Setting up relay from '
                    f'{listen_host}:{listen_port} to '
                    f'{connect_host}:{connect_port}')

        self.listen_addr = (listen_host, listen_port)
        self.connect_addr = (connect_host, connect_port)
        self.shutdown_signal = multiprocessing.Event()
        self.chunk_size = chunk_size
        self.delay_dist = delay_dist

    def set_distribution(self, distribution: Distribution):
        if not self.shutdown_signal.is_set():
            logger.info(f'Setting delay distribution to: {distribution}')
            self.delay_dist = distribution

    def run(self) -> None:
        if not self.delay_dist:
            logger.exception(RuntimeError('No delay distribution set for '
                                          'relay!'))

        signal.signal(signal.SIGINT, noop)  # remove signal handlers
        # connect sockets
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as l_sock:
            l_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            logger.info('Listening on {}:{}'.format(*self.listen_addr))
            l_sock.bind(self.listen_addr)
            l_sock.listen(0)

            with l_sock.accept()[0] as conn_a:
                addr_from = conn_a.getpeername()
                logger.info('Got connection from {}:{}'.format(*addr_from))
                logger.info('Connecting to {}:{}...'.format(*self.connect_addr))
                with socket.create_connection(self.connect_addr) as conn_b:
                    logger.info('Connected. Ready to relay between '
                                '{}:{} and {}:{}'.format(*addr_from,
                                                         *self.connect_addr))

                    relay_1 = SimplexRelay(conn_a, conn_b, self.delay_dist,
                                           self.chunk_size)
                    relay_2 = SimplexRelay(conn_b, conn_a, self.delay_dist,
                                           self.chunk_size)

                    relay_1.start()
                    relay_2.start()

                    self.shutdown_signal.wait()

                    logger.debug('Shutting down relay.')

                    relay_1.stop()
                    relay_2.stop()

                    conn_a.shutdown(socket.SHUT_RDWR)
                    conn_b.shutdown(socket.SHUT_RDWR)
                    l_sock.shutdown(socket.SHUT_RDWR)

        relay_1.join()
        relay_2.join()

        logger.debug('All simplex relays shut down.')

        self.shutdown_signal.clear()

    def stop(self):
        logger.debug('relay.stop() called!')
        self.shutdown_signal.set()
