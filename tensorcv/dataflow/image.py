# File: image.py
# Author: Qian Ge <geqian1001@gmail.com>
import os

import cv2
import numpy as np 
from scipy import misc

from .common import *
from .normalization import *
from .base import RNGDataFlow
from ..utils.common import check_dir

__all__ = ['ImageData', 'DataFromFile', 'ImageLabelFromFolder', 'ImageLabelFromFile', 'ImageFromFile']

class DataFromFile(RNGDataFlow):
    """ Base class for image from files """
    def __init__(self, ext_name, data_dir = '', 
                 num_channel = None,
                 shuffle = True, normalize = None,
                 normalize_fnc = identity):

        check_dir(data_dir)
        self.data_dir = data_dir
        self._shuffle = shuffle
        self._normalize = normalize
        self._normalize_fnc = normalize_fnc

        self.setup(epoch_val = 0, batch_size = 1)

        self._load_file_list(ext_name.lower())
        if self.size() == 0:
            print_warning('No {} files in folder {}'.\
                format(ext_name, data_dir))
        self.num_channels, self.im_size = self._get_im_size()
        self._data_id = 0

        if self._normalize == 'mean':
            self._mean = self._comp_mean() 

    def _comp_mean(self):
        return []

    def _load_file_list(self):
        raise NotImplementedError()

    def _get_im_size(self):
        # Run after _load_file_list
        # Assume all the image have the same size
        pass

    def _suffle_file_list(self):
        pass

    def next_batch(self):
        assert self._batch_size <= self.size(), \
        "batch_size cannot be larger than data size"

        start = self._data_id
        self._data_id += self._batch_size
        end = self._data_id
        # batch_file_range = range(start, end)

        if self._data_id + self._batch_size > self.size():
            self._epochs_completed += 1
            self._data_id = 0
            if self._shuffle:
                self._suffle_file_list()
        return self._load_data(start, end)

    def _load_data(self, start, end):
        raise NotImplementedError()

    # TODO to be modified 
    def _get_max_in_val(self):
        try:
            return self._max_in_val
        except AttributeError:
            self._max_in_val, self._half_in_val =\
             input_val_range(self.get_sample_data())
            return self._max_in_val

    def _get_half_in_val(self):
        try:
            return self._half_in_val
        except AttributeError:
            self._max_in_val, self._half_in_val =\
             input_val_range(self.get_sample_data())
            return self._half_in_val

    def _input_val_range(self, sample_data):
        # TODO to be modified  
        self._max_in_val, self._half_in_val = input_val_range(sample_data)

    def get_sample_data(self):
        return self._get_sample_data()

class ImageFromFile(DataFromFile):
    def __init__(self, ext_name, data_dir = '', 
                 num_channel = None,
                 shuffle = True, normalize = None,
                 normalize_fnc = identity,
                 reshape = None):
    
        if num_channel is not None:
            self.num_channels = num_channel
            self._read_channel = num_channel
        else:
            self._read_channel = None

        self._reshape = get_shape2D(reshape)

        super(ImageFromFile, self).__init__(ext_name, 
                                        data_dir = data_dir,
                                        shuffle = shuffle, 
                                        normalize = normalize,
                                        normalize_fnc = normalize_fnc)

    def _load_file_list(self, ext_name):
        im_dir = os.path.join(self.data_dir)
        self._im_list = get_file_list(im_dir, ext_name)
        if self._shuffle:
            self._suffle_file_list()

    def _suffle_file_list(self):
        idxs = np.arange(self.size())
        self.rng.shuffle(idxs)
        self._im_list = self._im_list[idxs]

    def _load_data(self, start, end):
        input_im_list = []
        for k in range(start, end):
            im_path = self._im_list[k]
            im = load_image(im_path, read_channel = self._read_channel)
            input_im_list.extend(im)

        # TODO to be modified 
        input_im_list = self._normalize_fnc(np.array(input_im_list), 
                                          self._get_max_in_val(), 
                                          self._get_half_in_val())

        return [input_im_list]

    def _get_sample_data(self):
        return load_image(self._im_list[0], read_channel = self._read_channel,
                          reshape = self._reshape)

    def _get_im_size(self):
        im = load_image(self._im_list[0], read_channel = self._read_channel,
                        reshape = self._reshape)
        if self._read_channel is None:
            self.num_channels = im.shape[3]
        self.im_size = [im.shape[1], im.shape[2]]
        return self.num_channels, self.im_size

    def size(self):
        return self._im_list.shape[0]

class ImageLabelFromFolder(ImageFromFile):
    """ read image data with label in subfolder name """
    def __init__(self, ext_name, data_dir = '', 
                 num_channel = None,
                 label_dict = None, num_class = None,
                 one_hot = False,
                 shuffle = True, normalize = None,
                 reshape = None):
        """
        Args:
           label_dict (dict): empty or full
        """

        # if num_channel is not None:
        #     self.num_channels = num_channel
        #     self._read_channel = num_channel
        # else:
        #     self._read_channel = None

        self._num_class = num_class
        self._one_hot = one_hot
        self.label_dict = label_dict
        super(ImageLabelFromFolder, self).__init__(ext_name, 
                                        data_dir = data_dir,
                                        num_channel = num_channel,
                                        shuffle = shuffle, 
                                        normalize = normalize,
                                        reshape = reshape)
        
        self.label_dict_reverse = reverse_label_dict(self.label_dict)

    def _load_file_list(self, ext_name):
        self._label_list = []
        self._im_list = []       

        folder_list = get_folder_names(self.data_dir)
        if self.label_dict is None or not bool(self.label_dict):
            self.label_dict = {}
            label_cnt = 0
            for folder_name in folder_list:
                if folder_name not in self.label_dict:
                    self.label_dict[folder_name] = label_cnt
                    label_cnt += 1
        if self._num_class is None:
            self._num_class = len(self.label_dict) 

        for folder_path, folder_name in zip(get_folder_list(self.data_dir), 
                                            get_folder_names(self.data_dir)):
            cur_folder_list = get_file_list(folder_path, ext_name)
            self._im_list.extend(cur_folder_list)
            self._label_list.extend([self.label_dict[folder_name] for i in range(len(cur_folder_list))])

        self._im_list = np.array(self._im_list)
        self._label_list = np.array(self._label_list)

        if self._one_hot:
            self._label_list = dense_to_one_hot(self._label_list, self._num_class)

        if self._shuffle:
            self._suffle_file_list()

    def _suffle_file_list(self):
        idxs = np.arange(self.size())
        self.rng.shuffle(idxs)
        self._im_list = self._im_list[idxs]
        self._label_list = self._label_list[idxs]

    def _load_data(self, start, end):
        input_im_list = []
        input_label_list = []
        for k in range(start, end):
            im_path = self._im_list[k]
            im = load_image(im_path, read_channel = self._read_channel, 
                            reshape = self._reshape)

            # if self._cv_read is not None:
            #     im = cv2.imread(im_path, self._cv_read)
            # else:
            #     im = misc.imread(im_path)

            # im = np.reshape(im, [1, im.shape[0], im.shape[1], self.num_channel])
            input_im_list.extend(im)

        input_label_list = np.array(self._label_list[start:end])
        input_im_list = np.array(input_im_list)

        if self._normalize == 'tanh':
            try:
                input_im_list = (input_im_list*1.0 - self._half_in_val)/\
                                 self._half_in_val
            except AttributeError:
                self._input_val_range(input_im_list[0])
                input_im_list = (input_im_list*1.0 - self._half_in_val)/\
                                 self._half_in_val

        return [input_im_list, input_label_list]

    # def _comp_mean(self):
    #     for im_path in self._im_list:
    #         im = cv2.imread(im_path, self._cv_read)

    def size(self):
        return self._im_list.shape[0]

    # def _get_im_size(self):
    #     im = load_image(self._im_list[0], read_channel = self._read_channel)
    #     # if self._cv_read is not None:
    #     #     im = cv2.imread(self._im_list[0], self._cv_read)
    #     # else:
    #     #     im = misc.imread(self._im_list[0])
    #     if self._read_channel is None:
    #         if len(im.shape) < 3:
    #             self.num_channel = 1
    #             # self._cv_read = cv2.IMREAD_GRAYSCALE
    #         else:
    #             self.num_channel = im.shape[2]
    #             # self._cv_read = cv2.IMREAD_COLOR
    #     self.im_size = [im.shape[0], im.shape[1]]
    #     return self.num_channel, self.im_size


class ImageLabelFromFile(ImageLabelFromFolder):
    """ read image data with label in a separate file txt """
    def __init__(self, ext_name, data_dir = '', 
                 label_file_name = '',
                 num_channel = None, one_hot = False,
                 label_dict = {}, num_class = None,
                 shuffle = True, normalize = None,
                 reshape = None):

        self._label_file_name = label_file_name
        super(ImageLabelFromFile, self).__init__(ext_name, 
                                    data_dir = data_dir, 
                                    num_channel = num_channel,
                                    label_dict = label_dict,
                                    num_class = num_class,
                                    one_hot = one_hot,
                                    shuffle = shuffle, 
                                    normalize = normalize,
                                    reshape = reshape)
        
    def _get_label_list(self):
        label_file = open(os.path.join(self.data_dir, 
                                       self._label_file_name),'r') 
        lines = label_file.read().split('\n')
        label_list = [line.split('\t')[1] 
                      for line in lines 
                      if len(line.split('\t')) > 2]
        label_file.close()

        if self.label_dict is None or not bool(self.label_dict):
            self.label_dict = {}
            label_cnt = 0
            for cur_label in label_list:
                if not cur_label in self.label_dict:
                    self.label_dict[cur_label] = label_cnt
                    label_cnt += 1
        if self._num_class is None:
            self._num_class = len(self.label_dict)
        
        return np.array([self.label_dict[cur_label] 
                        for cur_label in label_list])

    def _load_file_list(self, ext_name):
        self._im_list = get_file_list(self.data_dir, ext_name)
        self._label_list = self._get_label_list()

        if self._one_hot:
            self._label_list = dense_to_one_hot(self._label_list, self._num_class)

        if self._shuffle:
            self._suffle_file_list()


## TODO Add batch size
class ImageData(RNGDataFlow):
    def __init__(self, ext_name, data_dir = '', 
                 shuffle = True, normalize = None):
        assert os.path.isdir(data_dir)
        self.data_dir = data_dir

        self.shuffle = shuffle
        self._normalize = normalize

        self.setup(epoch_val = 0, batch_size = 1)
        self._load_file_list(ext_name.lower())
        self._get_im_size()
        self._data_id = 0

        self._read_channel = None

        # if num_channels > 1:
        #     self._cv_read = cv2.IMREAD_COLOR
        # else:
        #     self._cv_read = cv2.IMREAD_GRAYSCALE

    def _get_im_size(self):
        # Run after _load_file_list
        # Assume all the image have the same size
        # im = misc.imread(self.im_list[0])
        im = load_image(self.im_list[0])
        
        if len(im.shape) < 3:
            self.num_channels = 1
        else:
            self.num_channels = im.shape[2]
        self.im_size = [im.shape[0], im.shape[1]]
    
    def _load_file_list(self, ext_name):
        # TODO load other data as well
        im_dir = os.path.join(self.data_dir)
        self.im_list = get_file_list(im_dir, ext_name)

        if self.shuffle:
            self._suffle_file_list()
        return self.im_list

    def _load_data(self, batch_file_path):
        input_list = []
        for file_path in batch_file_path:
            # im = cv2.imread(self.im_list[self._data_id], self._cv_read)
            # print(file_path)
            # im = misc.imread(file_path)
            im = load_image(file_path, read_channel = self._read_channel)
            if len(im.shape) < 3:
                im = np.reshape(im, [1, im.shape[0], im.shape[1], 1])
            else:
                im = np.reshape(im, [1, im.shape[0], im.shape[1], im.shape[2]])
            input_list.extend(im)
        input_data = [np.array(input_list)]

        if self._normalize == 'tanh':
            try:
                input_data[0] = (input_data[0]*1.0 - self._half_in_val)/\
                                 self._half_in_val
            except AttributeError:
                self._input_val_range(input_data[0][0])
                input_data[0] = (input_data[0]*1.0 - self._half_in_val)/\
                                 self._half_in_val

        return input_data

    def _input_val_range(self, in_mat):
        # TODO to be modified  
        self._max_in_val, self._half_in_val = input_val_range(in_mat) 

    def next_batch(self):
        assert self._batch_size <= self.size(), \
        "batch_size cannot be larger than data size"

        start = self._data_id
        self._data_id += self._batch_size
        end = self._data_id
        batch_file_path = self.im_list[start:end]

        if self._data_id + self._batch_size > self.size():
            self._epochs_completed += 1
            self._data_id = 0
            if self.shuffle:
                self._suffle_file_list()
        return self._load_data(batch_file_path)

    def _suffle_file_list(self):
        idxs = np.arange(self.size())
        self.rng.shuffle(idxs)
        self.im_list = self.im_list[idxs]

    def size(self):
        return self.im_list.shape[0]  

if __name__ == '__main__':
    b = ImageLabelFromFolder('.jpeg',
        data_dir = 'D:\\Qian\\GitHub\\workspace\\dataset\\tiny-imagenet-200\\tiny-imagenet-200\\train\\',
                 shuffle = True, normalize = 'tanh', num_channel = 3, one_hot = True)
    # print(b.label_dict)
    print(b.next_batch()[0][:,30:40,30:40,:])
    print(b.next_batch()[1])
    
    a = ImageLabelFromFile('.jpeg',
        data_dir = 'D:\\Qian\\GitHub\\workspace\\dataset\\tiny-imagenet-200\\tiny-imagenet-200\\val\\',
                 shuffle = True, normalize = 'tanh', num_channel = 3,
                 label_file_name = 'val_annotations.txt', label_dict = b.label_dict, one_hot = True)
    print(a.next_batch()[0][:,30:40,30:40,:])
    print(a.next_batch()[1])
    # # print(a.next_batch()[0].shape)