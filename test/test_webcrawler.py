import threading

def test_add_to_task_queue(webcrawler_instance, config_instance):
    n_thread = int(config_instance['MAX_WORKER'])
    thread_list = []
    for i in range(n_thread):
        t = threading.Thread(target=webcrawler_instance._add_to_task_queue,
                             args=('http://www.test{i}.com'.format(i=i),))
        thread_list.append(t)

    for t in thread_list:
        t.start()

    for t in thread_list:
        t.join()

    url_set = set()
    for _ in range(webcrawler_instance.task_queue.qsize()):
        url = webcrawler_instance.task_queue.get()
        url_set.add(url)

    assert webcrawler_instance.total == n_thread + 1
    for i in range(n_thread):
        assert 'http://www.test{i}.com'.format(i=i) in url_set


def test_parse_html(webcrawler_instance):
    with open('test_html.html') as f:
        txt = f.read()
        parent_url = 'http://www.test.com/'
        webcrawler_instance._parse_html(txt, parent_url=parent_url)

        assert webcrawler_instance.total == 4

        url_set = set()
        for _ in range(webcrawler_instance.task_queue.qsize()):
            url = webcrawler_instance.task_queue.get()
            url_set.add(url)
        assert 'http://www.test.com/abc' in url_set
        assert 'http://www.test.com/def' in url_set
        assert 'http://www.test.com/ghi' in url_set
        assert 'http://www.test.com' in url_set

