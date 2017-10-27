#!/usr/bin/env python
# -*- coding: utf-8 -*-

# scrape_vor.py - load VOR website's Raw Content page using JS to scrape new media

import sys
import pprint
import re
import time
import unicodecsv as csv
from bs4 import BeautifulSoup
from selenium import webdriver

BASE_PATH        = '/Users/jcallender/work/vor/data/'
FULL_FILE        = BASE_PATH + 'all_videos.csv'
INCREMENTAL_FILE = BASE_PATH = 'incremental_videos.csv'

# obr data
leg_1_obr = {
    'team-akzonobel': 'Konrad Frost',
    'dongfeng-race-team': 'Richard Edwards',
    'mapfre': u'Ugo Fonollá',
    'vestas-11th-hour-racing': 'James Blake',
    'team-sun-hung-kai-scallywag': 'Jeremie Lecaudey',
    'turn-the-tide-on-plastic': 'Jen Edney',
    'team-brunel': u'Martin Keruzoré',
}
prologue_obr = {
    'team-akzonobel': 'James Blake',
    'dongfeng-race-team': 'Jeremie Lecaudey',
    'mapfre': 'Jen Edney',
    'vestas-11th-hour-racing': u'Martin Keruzoré',
    'team-sun-hung-kai-scallywag': 'Konrad Frost',
    'turn-the-tide-on-plastic': 'Sam Greenfield',
    'team-brunel': 'Richard Edwards',
}
obr = {
    'prologue': prologue_obr,
    'leg-01': leg_1_obr,
}

# team data
team_long_name = {
    'team-akzonobel': 'team AkzoNobel',
    'dongfeng-race-team': 'Dongfeng Race Team',
    'mapfre': 'MAPFRE',
    'vestas-11th-hour-racing': 'Vestas 11th Hour Racing',
    'team-sun-hung-kai-scallywag': 'Sun Hung Kai/Scallywag',
    'turn-the-tide-on-plastic': 'Turn the Tide on Plastic',
    'team-brunel': 'Team Brunel',
}

# leg label
pretty_leg = {
    'prologue': 'Prologue',
    'leg-01': '1',
}

def main():
    browser   = webdriver.Chrome('/Users/jcallender/bin/chromedriver')
    url       = "http://www.volvooceanrace.com/en/raw.html"
    browser.get(url)

    # //*[@id="angular-raw"]/header/ul/li[4]/a
    enable_video_link = browser.find_element_by_xpath("//*[@id='angular-raw']/header/ul/li[4]/a")
    if enable_video_link and enable_video_link.is_enabled():
        enable_video_link.click()

    # //*[@id="angular-raw"]/header/ul/li[4]/ul/li[3]/a
    video_link = browser.find_element_by_xpath("//*[@id='angular-raw']/header/ul/li[4]/ul/li[3]/a")
    if video_link and video_link.is_enabled():
        video_link.click()
        time.sleep(10)

    for i in range(0, 20):
        load_more_button = browser.find_element_by_css_selector('a.load-more-bt')
        if load_more_button and load_more_button.is_enabled():
            try:
                load_more_button.click()
            except:
                break
            time.sleep(10)
        else:
            break

    innerHTML = browser.execute_script("return document.body.innerHTML")
    soup      = BeautifulSoup(innerHTML, 'html.parser')

    # print(soup.prettify())

    items = []
    for raw_item in soup.find_all('li', class_='content-angular-raw-item'):
        item = scrape_item(browser, raw_item)
        items.append(item)

    full_file_data = []
    for item in items:
        if item['type'] != 'video':
            continue
        pretty_data = {
            'Datetime': item['datetime'],
            'Leg': pretty_leg[item['leg']],
            'Team': team_long_name[item['team']],
            'OBR': obr[item['leg']][item['team']],
            'Video': """=HYPERLINK("%s", IMAGE("%s"))""" % (item['source_url'], item['preview_url']),
            'Length': '',
            'People': '',
            'Description': '',
            'Tags': '',
        }
        full_file_data.append(pretty_data)

    with open(FULL_FILE, 'w') as full_file:
        # fieldnames = ['datetime', 'leg', 'team', 'type', 'preview_url', 'source_url']
        fieldnames = ['Datetime', 'Leg', 'Team', 'OBR', 'Video', 'Length', 'People', 'Description', 'Tags']
        writer = csv.DictWriter(full_file, fieldnames=fieldnames)
        writer.writeheader()
        for item in full_file_data:
            writer.writerow(item)

    # TBD:
    # - automatically update the sheet
    # - schedule the job to run under cron (or the equivalent)

def scrape_item(browser, raw_item):
    item = {}
    class_tags = raw_item.get('class') # list of strings
    if class_tags[2] == 'date':
        item = scrape_date_item(raw_item, class_tags, item)
    else:
        item = scrape_non_date_item(browser, raw_item, class_tags, item)
    item['datetime'] = raw_item.footer.time['datetime']
    return item

def scrape_date_item(raw_item, class_tags, item):
        item = {}
        item['type'] = 'date'
        return item

def scrape_non_date_item(browser, raw_item, class_tags, item):
    item = {
        'leg': class_tags[2],
        'type': class_tags[3],
        'team': class_tags[4],
    }
    if len(class_tags) >= 6:
        item['no-img'] = class_tags[5]

    if item['type'] == 'social':
        item = scrape_social_item(raw_item, item)
    elif item['type'] == 'photo':
        item = scrape_photo_item(browser, raw_item, item)
    elif item['type'] == 'video':
        item = scrape_video_item(raw_item, item)
    else:
        raise ValueError('Unable to determine item type for item: ' + str(raw_item))

    return item

def scrape_social_item(raw_item, item):
    return item

def scrape_photo_item(browser, raw_item, item):
    item['source_url'] = raw_item.img['src']
    return item

def scrape_video_item(raw_item, item):
    item['preview_url'] = raw_item.img['src']
    item['source_url'] = item['preview_url']
    item['source_url'] = re.sub(r'thumb/', '', item['source_url'])
    item['source_url'] = re.sub(r'_[0-9]{5}_[0-9x]+\.jpg$', '_HD.mp4', item['source_url'])
    return item


main()


'''
DATE ITEM:

<li class="content-angular-raw-item more-items-item date" ng-repeat="item in pagedItemsLoaded" style="position: absolute; left: 0px; top: 14px;">
<div class="item-img-container" ng-style="imgBackgroundOverlay(item)" on-finish-render="">
<div class="video-play"></div>
<div class="item-img-mask"></div>
<!-- ngIf: item.mediaShow && !item.mediaVideo -->
<!-- ngIf: item.mediaVideoMulti -->
<!-- ngIf: item.mediaVideo && !item.mediaVideoMulti -->
</div>
<div class="wrapper">
<!-- ngIf: item.icon -->
<!-- ngIf: item.category -->
<!-- ngIf: item.subcategory -->
<!-- ngIf: item.tagName -->
<h2 class="ng-binding"></h2>
<!-- ngIf: item.subtitle -->
<!-- ngIf: item.short_text -->
<!-- ngIf: item.plus_text -->
<!-- ngIf: item.plus_text -->
<!-- ngIf: item.code -->
<!-- ngIf: item.social -->
</div>
<footer>
<!-- ngIf: item.subsection -->
<!-- ngIf: item.date --><time class="item-time ng-scope" datetime="2017-10-26 15:52:38" ng-if="item.date">
<span class="date ng-binding">October 26, 2017 </span>
<span class="date-time ng-binding">15:52 UTC</span>
</time><!-- end ngIf: item.date -->
</footer>
<a class="all-box-link" ng-click="openModalData('modal-angular-data', item)" target="_self"></a>
</li>

SOCIAL ITEM:

<li class="content-angular-raw-item more-items-item leg-01 social turn-the-tide-on-plastic no-img" ng-repeat="item in pagedItemsLoaded" style="position: absolute; left: 293px; top: 114px;">
<div class="item-img-container" ng-style="imgBackgroundOverlay(item)" on-finish-render="">
<div class="video-play"></div>
<div class="item-img-mask"></div>
<!-- ngIf: item.mediaShow && !item.mediaVideo --><img class="more-items-img ng-scope hide show spinner-show" imageonload="" ng-if="item.mediaShow &amp;&amp; !item.mediaVideo" ng-src="//www.volvooceanrace.com/static/assets/2017-18/dist/img/no-image.jpg" src="//www.volvooceanrace.com/static/assets/2017-18/dist/img/no-image.jpg" style=""/><!-- end ngIf: item.mediaShow && !item.mediaVideo -->
<!-- ngIf: item.mediaVideoMulti -->
<!-- ngIf: item.mediaVideo && !item.mediaVideoMulti -->
</div>
<div class="wrapper">
<!-- ngIf: item.icon -->
<!-- ngIf: item.category -->
<!-- ngIf: item.subcategory -->
<!-- ngIf: item.tagName -->
<h2 class="ng-binding">Lucas and his snuggle buddy!</h2>
<!-- ngIf: item.subtitle -->
<!-- ngIf: item.short_text -->
<!-- ngIf: item.plus_text -->
<!-- ngIf: item.plus_text -->
<!-- ngIf: item.code -->
<!-- ngIf: item.social --><social-post-preview class="ng-scope ng-isolate-scope" data-social="item.social" ng-if="item.social"><iframe allowtransparency="true" class="instagram-media ng-scope instagram-media-rendered" data-instgrm-payload-id="instagram-media-payload-0" frameborder="0" height="387" id="instagram-embed-0" scrolling="no" src="https://www.instagram.com/p/Bat4SRRjpKy/embed/captioned/?cr=1&amp;v=7&amp;wp=554#%7B%22ci%22%3A0%2C%22os%22%3A3815.23%7D" style="background: rgb(255, 255, 255); border: 1px solid rgb(219, 219, 219); margin: 1px 1px 12px; max-width: 658px; width: calc(100% - 2px); border-radius: 4px; box-shadow: none; display: block; padding: 0px;"></iframe>
<script async="" class="ng-scope" defer="" src="//platform.instagram.com/en_US/embeds.js"></script></social-post-preview><!-- end ngIf: item.social -->
</div>
<footer>
<!-- ngIf: item.subsection --><div class="item-subsection ng-scope ng-isolate-scope" ng-bind-html-unsafe="item.subsection" ng-if="item.subsection"><div class="ng-binding" ng-bind-html="trustedHtml">Turn the Tide on Plastic</div></div><!-- end ngIf: item.subsection -->
<!-- ngIf: item.date --><time class="item-time ng-scope" datetime="2017-10-26 15:50:09" ng-if="item.date">
<span class="date ng-binding">October 26, 2017 </span>
<span class="date-time ng-binding">15:50 UTC</span>
</time><!-- end ngIf: item.date -->
</footer>
<a class="all-box-link" ng-click="openModalData('modal-angular-data', item)" target="_self"></a>
</li>

PHOTO ITEM:

<li class="content-angular-raw-item more-items-item leg-01 photo dongfeng-race-team" ng-repeat="item in pagedItemsLoaded" style="position: absolute; left: 0px; top: 285px;">
<div class="item-img-container" ng-style="imgBackgroundOverlay(item)" on-finish-render="">
<div class="video-play"></div>
<div class="item-img-mask"></div>
<!-- ngIf: item.mediaShow && !item.mediaVideo --><img class="more-items-img ng-scope hide show spinner-show" imageonload="" ng-if="item.mediaShow &amp;&amp; !item.mediaVideo" ng-src="https://www.volvooceanrace.com/static/assets/2017-18/cropped/1051/m105089_crop110015_800x800_proportional_1509030907F2FC.jpg" src="https://www.volvooceanrace.com/static/assets/2017-18/cropped/1051/m105089_crop110015_800x800_proportional_1509030907F2FC.jpg" style=""/><!-- end ngIf: item.mediaShow && !item.mediaVideo -->
<!-- ngIf: item.mediaVideoMulti -->
<!-- ngIf: item.mediaVideo && !item.mediaVideoMulti -->
</div>
<div class="wrapper">
<!-- ngIf: item.icon -->
<!-- ngIf: item.category -->
<!-- ngIf: item.subcategory -->
<!-- ngIf: item.tagName -->
<h2 class="ng-binding">13_01_171026_DFG_RCE_00009.jpg</h2>
<!-- ngIf: item.subtitle -->
<!-- ngIf: item.short_text -->
<!-- ngIf: item.plus_text -->
<!-- ngIf: item.plus_text -->
<!-- ngIf: item.code -->
<!-- ngIf: item.social -->
</div>
<footer>
<!-- ngIf: item.subsection --><div class="item-subsection ng-scope ng-isolate-scope" ng-bind-html-unsafe="item.subsection" ng-if="item.subsection"><div class="ng-binding" ng-bind-html="trustedHtml">Dongfeng Race Team</div></div><!-- end ngIf: item.subsection -->
<!-- ngIf: item.date --><time class="item-time ng-scope" datetime="2017-10-26 15:13:54" ng-if="item.date">
<span class="date ng-binding">October 26, 2017 </span>
<span class="date-time ng-binding">15:13 UTC</span>
</time><!-- end ngIf: item.date -->
</footer>
<a class="all-box-link" ng-click="openModalData('modal-angular-data', item)" target="_self"></a>
</li>

VIDEO ITEM:

<li class="content-angular-raw-item more-items-item leg-01 video mapfre" ng-repeat="item in pagedItemsLoaded" style="position: absolute; left: 380px; top: 3847px;">
    <div class="item-img-container" on-finish-render="" ng-style="imgBackgroundOverlay(item)">
        <div class="video-play"></div>
        <div class="item-img-mask"></div>
        <!-- ngIf: item.mediaShow && !item.mediaVideo -->
        <!-- ngIf: item.mediaVideoMulti --><img ng-src="https://volvooceanrace-2017-18.s3.amazonaws.com/videos/cropped/thumb/m105094_13-01-171026-mpf-ugf-00003_00002_480x270.jpg" class="more-items-img ng-scope hide show spinner-show" imageonload="" ng-if="item.mediaVideoMulti" src="https://volvooceanrace-2017-18.s3.amazonaws.com/videos/cropped/thumb/m105094_13-01-171026-mpf-ugf-00003_00002_480x270.jpg" style=""><!-- end ngIf: item.mediaVideoMulti -->
        <!-- ngIf: item.mediaVideo && !item.mediaVideoMulti -->

    </div>
    <div class="wrapper">
        <!-- ngIf: item.icon -->
        <!-- ngIf: item.category -->
        <!-- ngIf: item.subcategory -->
        <!-- ngIf: item.tagName -->
        <h2 class="ng-binding">13_01_171026_MPF_UGF_00003.mp4</h2>
        <!-- ngIf: item.subtitle -->
        <!-- ngIf: item.short_text -->
        <!-- ngIf: item.plus_text -->
        <!-- ngIf: item.plus_text -->
        <!-- ngIf: item.code -->
        <!-- ngIf: item.social -->
    </div>
    <footer>
        <!-- ngIf: item.subsection --><div class="item-subsection ng-scope ng-isolate-scope" ng-bind-html-unsafe="item.subsection" ng-if="item.subsection"><div ng-bind-html="trustedHtml" class="ng-binding">MAPFRE</div></div><!-- end ngIf: item.subsection -->
        <!-- ngIf: item.date --><time class="item-time ng-scope" ng-if="item.date" datetime="2017-10-26 15:52:38">
            <span class="date ng-binding">October 26, 2017 </span>
            <span class="date-time ng-binding">15:52 UTC</span>
        </time><!-- end ngIf: item.date -->
    </footer>
    <a class="all-box-link" ng-click="openModalData('modal-angular-data', item)" target="_self"></a>
</li>

Note that the above item ended up playing a video from the URL created by going from this:

https://volvooceanrace-2017-18.s3.amazonaws.com/videos/cropped/thumb/m105094_13-01-171026-mpf-ugf-00003_00002_480x270.jpg

to this:

https://volvooceanrace-2017-18.s3.amazonaws.com/videos/cropped/m105094_13-01-171026-mpf-ugf-00003_HD.mp4

...which means I need to:

* truncate path to remove the trailing 'thumb/'
* truncate to the following portion of the filename: m{^[a-z]\d+_\d{2}\-\d{2}\-\d+[-a-z]+\d+}
* append '_HD.mp4'

'''
