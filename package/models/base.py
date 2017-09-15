from abc import abstractmethod

import tensorflow as tf


__all__ = ['ModelDes', 'BaseModel']

class ModelDes(object):
    """ base model for ModelDes """
    def get_placeholder(self):
        return self._get_placeholder()

    def _get_placeholder(self):
        raise NotImplementedError()

    def create_graph(self):
        self._create_graph()

    @abstractmethod
    def _create_graph(self):
        raise NotImplementedError()


class BaseModel(ModelDes):
    """ Model with single loss and single optimizer """

    def get_optimizer(self):
        return self._get_optimizer()

    def _get_optimizer(self):
        raise NotImplementedError()

    def get_loss(self):
        return self._get_loss()

    def _get_loss(self):
        raise NotImplementedError()

    def get_grads(self):
        optimizer = self.get_optimizer()
        loss = self.get_loss()
        grads = optimizer.compute_gradients(loss)
        return grads










