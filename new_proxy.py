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
import socket
import time

from logzero import logger

from distributions import Distribution

multiprocessing.allow_connection_pickling()


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
        from_addr = self.conn_a.getpeername()
        to_addr = self.conn_b.getpeername()
        logger.info('Relaying data from '
                    '{}:{} to {}:{}'.format(*from_addr, *to_addr))
        while not self.shutdown_signal.is_set():
            try:
                data = self.conn_a.recv(self.chunk_size)
                time.sleep(self.delay_dist.sample())
                self.conn_b.sendall(data)
            except socket.error as e:
                logger.warning(e)
                break
            except Exception as e:
                logger.exception(e)
                break

    def stop(self) -> None:
        self.shutdown_signal.set()
