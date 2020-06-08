import os
import pytest
import configparser
from webCrawler.webCrawler import WebCrawler


@pytest.fixture
def webcrawler_instance():
    """ Create an instance of web crawler

        :return: crawler
    """
    config = configparser.ConfigParser()
    dir_name = os.path.realpath('..')
    config.read(os.path.join(dir_name, 'crawler_config'))
    test_url = 'http://www.test.com'
    crawler = WebCrawler(test_url, config['TEST'])
    return crawler


@pytest.fixture
def config_instance():
    """ Create an instance of test config

        :return: config
    """
    config = configparser.ConfigParser()
    dir_name = os.path.realpath('..')
    config.read(os.path.join(dir_name, 'crawler_config'))
    return config['TEST']


@pytest.fixture(scope="session", autouse=True)
def cleanup():
    """ Cleanup a testing directory once we are finished.
    """
    if os.path.exists("webCrawler.log"):
        os.remove("webCrawler.log")