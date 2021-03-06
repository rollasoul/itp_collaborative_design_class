from __future__ import print_function

import os
import datetime
import re
import time

import numpy as np
import requests
import caffe

OUTPUT_DIR = 'data'

# locate important imagenet data file installed with caffe
IMAGENET_DATA_FILE = os.path.join(
    os.path.split(caffe.__file__)[0], 'imagenet', 'ilsvrc_2012_mean.npy')


def get_img_urls(tag, limit):
    url = 'https://www.instagram.com/explore/tags/{0}/'.format(tag)
    response = requests.get(url)
    # poorly written regex for parsing out the urls
    image_urls = re.findall(r"https://scontent[^x]*?jpg", response.text)

    image_urls = np.random.choice(image_urls, limit, replace=False)

    return image_urls


def download_images(image_urls):
    now = datetime.datetime.now()
    output_dir = os.path.join(OUTPUT_DIR, now.strftime('%Y%m%d_%H%M%S'))
    os.makedirs(output_dir)

    img_data = list(enumerate(image_urls))

    for num, url in img_data:
        print('downloading {0}'.format(url))
        response = requests.get(url)
        with open(os.path.join(output_dir, '{}.jpg'.format(num)), 'wb') as f:
            f.write(response.content)
        time.sleep(1 + np.random.normal(0, 1)**2)

    return output_dir, img_data


def evaluate_images(output_dir, img_data):
    model_def = 'memnet/deploy.prototxt'
    model_weights = 'memnet/memnet.caffemodel'

    net = caffe.Net(model_def, model_weights, caffe.TEST)

    mu = np.load(IMAGENET_DATA_FILE).mean(1).mean(1)

    # create transformer for the input called 'data'
    transformer = caffe.io.Transformer({'data': net.blobs['data'].data.shape})

    transformer.set_transpose('data', (2, 0, 1))
    transformer.set_mean('data', mu)
    transformer.set_raw_scale('data', 255)
    transformer.set_channel_swap('data', (2, 1, 0))

    net.blobs['data'].reshape(len(img_data), 3, 227, 227)

    for num, url in img_data:
        img = caffe.io.load_image(
            os.path.join(output_dir, '{0}.jpg'.format(num)))
        transformed_img = transformer.preprocess('data', img)
        net.blobs['data'].data[num, ...] = transformed_img

    nn_values = list(net.forward().values())[0]

    result = [(a[0], a[1], b[0]) for a, b in zip(img_data, nn_values)]

    return result


def make_html(output_dir, data, best_limit):
    data = sorted(data, key=lambda x: x[2], reverse=True)[:best_limit]
    body = ''.join(['<div>{1}<img src="{0}.jpg"></div>'.format(i, r)
                    for i, _, r in data])

    html = "<html><head></head><body>{0}</body></html>".format(body)

    with open(os.path.join(output_dir, 'out.html'), 'w') as f:
        f.write(html)


def demo(tag, limit=10, best_limit=5):
    image_urls = get_img_urls(tag, limit)
    output_dir, img_data = download_images(image_urls)
    data = evaluate_images(output_dir, img_data)
    make_html(output_dir, data, best_limit)

    print('Output written to', output_dir)
