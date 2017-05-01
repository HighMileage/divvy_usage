from bs4 import BeautifulSoup
from flask import Flask, render_template
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from station_list import STATIONS
from collections import namedtuple
import csv
import os
import time

app = Flask(__name__)


def _parse_creds(filename='.divvy'):
    """ Parses dot file for lacrm credentials """

    creds = None

    try:
        file_path = os.path.expanduser('~') + '/' + filename
        with open(file_path, 'r') as credfile:
            for line in credfile:
                if line.strip()[0] == '#':
                    pass
                elif ':' in line:
                    username = line.strip().split(':')[0]
                    password = line.strip().split(':')[1]
                    creds = username, password
                    break
        return creds

    # Fail silently as most people will not have creds file
    except IOError:
        return None

    except (UnboundLocalError, IndexError):
        print('Attempted to use a credentials dotfile ({}) but '
              'it is either empty or malformed. Credentials should be in '
              'the form <USERNAME>:<API_TOKEN>.'.format(file_path))
        raise


def wait_for(condition_function):
    """ Helper method """
    start_time = time.time()
    while time.time() < start_time + 10:
        if condition_function:
            return True
        else:
            time.sleep(0.1)
        raise Exception(
            'Timeout waiting for {}'
            .format(condition_function.__name__)
        )


def get_new_url(driver, link_text):
    """
    Helper to try and ensure page loads completely before grabbing page source.
    """

    link = driver.get(link_text)

    def link_has_gone_stale():
        try:
            # poll the link with an arbitrary call
            link.find_element_by_tag_name('html')
            return False
        except StaleElementReferenceException:
            return True
    wait_for(link_has_gone_stale)


def trip_list():
    try:
        username, password = _parse_creds()
        # wget https://github.com/mozilla/geckodriver/releases/download/v0.16.1/geckodriver-v0.16.1-macos.tar.gz
        caps = {
            "alwaysMatch":
            {"moz:firefoxOptions": {"binary":
                                    "/Applications/Firefox.app/Contents/MacOS/firefox.bin"}}}
        driver = webdriver.Firefox(capabilities=caps)
        get_new_url(driver, 'https://member.divvybikes.com/login')

        driver.find_element_by_name('subscriberUsername').send_keys(username)
        driver.find_element_by_name('subscriberPassword').send_keys(password)
        driver.find_element_by_name('login_submit').click()

        get_new_url(driver, 'https://member.divvybikes.com/account/trips')
        driver.find_element_by_link_text('Last ›').click()
        total_pages = int(driver.current_url.split('/')[-1]) + 1

        pages = []
        for page in list(range(1, total_pages)):
            get_new_url(driver, 'https://member.divvybikes.com/account/trips/{}'.format(page))
            pages.append(BeautifulSoup(driver.page_source, 'html.parser'))

        time.sleep(3)
        driver.close()

        return process_pages(pages)

    except Exception as e:
        driver.close()
        print('We fucked up')
        raise e


def process_pages(pages, write_to_disk=False):
    """ Write out to CSV """

    detailed_rows = []
    Trip = namedtuple(
        'Trip',
        ['id',
            'start_station',
            'start_time',
            'end_station',
            'end_time',
            'duration']
    )

    for page in pages:
        for row in page.find_all('tr')[1:]:
            detailed_rows.append(Trip(
                row.get('id'),
                row.get('data-start-station-id'),
                row.get('data-start-timestamp'),
                row.get('data-end-station-id'),
                row.get('data-end-timestamp'),
                row.get('data-duration-seconds')
            ))

    if write_to_disk:
        with open('output.csv', 'wt') as csv_output:
            csv_writer = csv.writer(csv_output)
            for row in detailed_rows:
                csv_writer.writerow(row)

    else:
        uniques = []
        for trip in detailed_rows:
            uniques.append(trip.start_station)
            uniques.append(trip.end_station)
        return set(uniques)


@app.route('/station_usage')
def dashboard():
    trips = trip_list()
    station_list = STATIONS

    return render_template('index.html',
                           stations=station_list,
                           trips=trips,
                           coverage=round(len(trips)/len(station_list)*100.0, 1)
                           )

if __name__ == '__main__':
    app.run(debug=True)
