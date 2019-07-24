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

import numpy as np
from functools import partial


class Distribution:
    """
    Interface for statistical distributions
    """

    def sample(self) -> float:
        pass


class ConstantDistribution(Distribution):
    def __init__(self, constant: float):
        super().__init__()
        self.constant = constant

    def sample(self) -> float:
        return self.constant

    def __repr__(self):
        return f'ConstantDistribution(constant={self.constant})'

    def __str__(self):
        return f'Constant distribution (constant: {self.constant})'


class GaussianDistribution(Distribution):
    def __init__(self, mean: float, std_dev: float,
                 strictly_positive: bool = True):
        super().__init__()
        self.mean = mean
        self.std_dev = std_dev
        self.dist = partial(np.random.normal, loc=mean, scale=std_dev)
        self.positive = strictly_positive

    def sample(self) -> float:
        if self.positive:
            return max(self.dist(), 0.0)
        else:
            return self.dist()

    def __repr__(self):
        return f'GaussianDistribution(' \
            f'mean={self.mean}, ' \
            f'std_dev={self.std_dev}, ' \
            f'strictly_positive={self.positive})'

    def __str__(self):
        return f'Gaussian distribution ' \
            f'(mean: {self.mean}, standard deviation: {self.std_dev})'


class ExponentialDistribution(Distribution):
    def __init__(self, scale: float):
        super().__init__()
        self.scale = scale
        self.dist = partial(np.random.exponential, scale=scale)

    def sample(self) -> float:
        return self.dist()

    def __repr__(self):
        return f'ExponentialDistribution(scale={self.scale})'

    def __str__(self):
        return f'Exponential distribution (scale: {self.scale})'
