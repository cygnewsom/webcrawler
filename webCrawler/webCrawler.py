import requests
import logging
import time
import concurrent
import configparser
from threading import Lock
from queue import Queue, Empty, Full
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

from bloom_filter import BloomFilter
from bs4 import BeautifulSoup

logger = logging.getLogger('webCrawler')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('webCrawler.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s: %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

class WebCrawler:
    """ The WebCrawler class implements a multithreaded web crawler starting from the base_url.

        The crawler runs based on the breadth-first search algorithm and starts running from the
        base_url and parsing the content to get more urls to be crawled.

        :param  base_url:       the input of the starting url of the web crawling
        :param  closure_url:    the stopping condition is based on this parameter
        :param  pool:           the threadpool
        :param  task_queue:     the task_queue that include all the urls that need to be crawled
        :param  crawled_pages:  a bloom filter used to eliminated visited pages from the BFS algorithm
        :param  total:          counter for the total number of pages being crawled
        :param  lock:           mutex lock to prevent race condition when read/write crawled_pages
        :param  run_time:       timer for the time spent on running the web crawler
    """
    def __init__(self, base_url: str, cfg: configparser)->None:
        self.base_url = base_url
        self.config = cfg
        self.closure_url = '{scheme}://{netloc}'.format(scheme=urlsplit(self.base_url).scheme,
                                                        netloc=urlsplit(self.base_url).netloc)
        self.pool = ThreadPoolExecutor(max_workers=int(self.config['MAX_WORKER']))
        self.task_queue = Queue(maxsize=3*int(self.config['MAX_WORKER']))
        self.task_queue.put(self.base_url)
        self.crawled_pages = BloomFilter(max_elements=int(self.config['MAX_ELEMENTS']),
                                         error_rate=float(self.config['ERROR_RATE']))
        self.crawled_pages.add(self.base_url)
        self.total = 1
        self.lock = Lock()
        self.run_time = time.time()

    def _add_to_task_queue(self, child_url) -> None:
        """ Add url to the task queue concurrently

        If the child_url pass the bloom filter, it will be added to the task queue

        :param child_url:   the url to be added to the task queue
        :return: None
        """
        ret = self.lock.acquire(timeout=int(self.config['TIMEOUT']))
        if ret:
            if child_url not in self.crawled_pages:
                self.crawled_pages.add(child_url)
                self.total += 1
                self.lock.release()
                try:
                    self.task_queue.put(child_url, block=True, timeout=int(self.config['TIMEOUT']))
                except Full:
                    logger.error("Task queue full when putting {child_url}".format(child_url=child_url))
                else:
                    logger.info("\t{child_url}".format(child_url=child_url))
            else:
                self.lock.release()
        else:
            logger.error("Lock timed out.")

    def _parse_html(self, html: str, parent_url: str) -> None:
        """ Parse the html content of the page from the parent_url.

            Get all the urls (must start with the closure_url as the stopping condition)
            from the html page and add them to the task queue.

            :param  html:       the html content of the parent_url
            :param  parent_url: the url of the html page to be parsed
            :return None
        """
        soup = BeautifulSoup(html, 'html.parser')
        links = soup.find_all('a', href=True)
        logger.info("{parent_url}".format(parent_url=parent_url))
        for link in set(links):
            child_url = link['href']
            if child_url.startswith('/') or child_url.startswith(self.closure_url):
                child_url = urljoin(self.closure_url, child_url)
                if child_url.endswith('/'):
                    child_url = child_url[:-1]
                    self._add_to_task_queue(child_url)

    def _callback(self, res: concurrent.futures) -> None:
        """ Callback when the html page is downloaded.

            :param  res: the request used to fetch the html page in _get_page
            :return None
        """
        result, url = res.result()
        if not result:
            return
        if result.status_code == 200 and 'html' in result.headers['content-type']:
            self._parse_html(result.text, url)
        elif result.status_code in (301, 302):
            redirect_url = result.headers['Locations']
            if redirect_url.endswith('/'):
                redirect_url = redirect_url[:-1]
                logger.debug("{url} is redirected to {redirect_url}".format(url=url, redirect_url=redirect_url))
                self._add_to_task_queue(redirect_url)

    def _get_page(self, url: str) -> (requests, str):
        """ Get the page from the url

            :param  url: the input of requests
            :return (requests, url)
        """
        try:
            res = requests.get(url, timeout=int(self.config['TIMEOUT']))
            return res, url
        except requests.RequestException as e:
            logger.warning('{e} for {url}'.format(e=e, url=url))
            return None, url

    def run(self) -> None:
        """ Run the webcrawler in a parallel fashion. The workers managed by
            the thread pool get tasks from the shared task queue. Once the worker
            is fired, it will get the url page by calling _get_page. When the page
            is got, the _callback will be called to parse the page to get more urls
            to be added to the task queue.
        """
        while True:
            try:
                target_url = self.task_queue.get(timeout=int(self.config['TIMEOUT']))
                job = self.pool.submit(self._get_page, target_url)
                job.add_done_callback(self._callback)
            except Empty:
                return
            except Exception as e:
                logger.warning(e)
                continue

    def report(self) -> None:
        """ Report the wall time and total pages on the web crawler
        """
        self.pool.shutdown(wait=True)
        self.run_time = time.time() - self.run_time
        logger.info("{time:.2f} seconds is spent to crawl on {total} pages".format(time=self.run_time, total=self.total))



