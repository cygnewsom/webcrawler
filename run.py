import sys
import configparser
import logging
from webCrawler.webCrawler import WebCrawler


if __name__ == '__main__':
    logger = logging.getLogger('webCrawler')
    if len(sys.argv) < 2:
        print("Please provide the base url for the web crawler to start. "
              "Eg. > python webCrawler.py http(s)://www.[my_root].com")
        logger.error("Not enough arguments provided from command {argv}. Quit.".format(argv=str(sys.argv)))
        exit(1)
    inputUrl = sys.argv[1]
    if not (inputUrl.startswith('http://') or inputUrl.startswith('https://')):
        print("Please specify the scheme in either http or https.")
        logger.error("{inputUrl} provided doesn't specify scheme. Quit.".format(inputUrl=inputUrl))
        exit(1)
    config = configparser.ConfigParser()
    config.read('crawler_config')
    crawler = WebCrawler(inputUrl, config['DEFAULT'])
    crawler.run()
    crawler.report()