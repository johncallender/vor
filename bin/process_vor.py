#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# process_vor.py - load VOR website's Raw Content page using their raw.json file

from __future__ import print_function

import sys
import pprint
import time
import urllib2
import json

# for Google Sheets API
from apiclient import discovery
from httplib2 import Http
from oauth2client import file, client, tools

# SPREADSHEET_ID = '1WVwCp5qwKKfOeAnyFJyDjAIINpPhrj_FQC20DJ7StW8' # live copy
SPREADSHEET_ID = '1A6W6VQXGJgcLDV-omZrbrghY7UypKJqSmaKxHQm-EfA' # QA copy for testing

# obr data
leg_2_obr = {
    'team-akzonobel': 'James Blake',
    'dongfeng-race-team': 'Jérémie Lecaudey',
    'mapfre': u'Ugo Fonollá',
    'vestas-11th-hour-racing': 'Martin Keruzore',
    'team-sun-hung-kai-scallywag': 'Konrad Frost',
    'turn-the-tide-on-plastic': 'Sam Greenfield',
    'team-brunel': 'Richard Edwards',
}
leg_1_obr = {
    'team-akzonobel': 'Konrad Frost',
    'dongfeng-race-team': 'Richard Edwards',
    'mapfre': u'Ugo Fonollá',
    'vestas-11th-hour-racing': 'James Blake',
    'team-sun-hung-kai-scallywag': 'Jérémie Lecaudey',
    'turn-the-tide-on-plastic': 'Jen Edney',
    'team-brunel': u'Martin Keruzoré',
}
prologue_obr = {
    'team-akzonobel': 'James Blake',
    'dongfeng-race-team': 'Jérémie Lecaudey',
    'mapfre': 'Jen Edney',
    'vestas-11th-hour-racing': u'Martin Keruzoré',
    'team-sun-hung-kai-scallywag': 'Konrad Frost',
    'turn-the-tide-on-plastic': 'Sam Greenfield',
    'team-brunel': 'Richard Edwards',
}
obr = {
    'prologue': prologue_obr,
    'leg-01': leg_1_obr,
    'leg-02': leg_2_obr,
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
    'leg-02': '2',
}

# Google Sheets API access
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
store = file.Storage('/Users/jcallender/work/vor/etc/passwords/storage.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('/Users/jcallender/work/vor/etc/passwords/client_id.json', SCOPES)
    creds = tools.run_flow(flow, store)
SHEETS = discovery.build('sheets', 'v4', http=creds.authorize(Http()))

def main():
    all_videos = read_full_spreadsheet()
    seen = {}
    for item in all_videos:
        seen_key = get_seen_key(item)
        seen[seen_key] = True

    response = urllib2.urlopen('http://www.volvooceanrace.com/en/raw.json')
    raw_json = response.read()
    raw_items = json.loads(raw_json)

    items = []
    for raw_item in raw_items:
        item = process_item(raw_item)
        items.append(item)

    new_videos = []
    for item in items:
        if item['type'] != 'video':
            continue
        pretty_data = {
            'Datetime': """=HYPERLINK("%s", "%s")""" % (item['vor_url'], item['datetime']),
            'Leg': pretty_leg[item['leg']],
            'Team': team_long_name[item['team']],
            'OBR': obr[item['leg']][item['team']],
            'Video': """=HYPERLINK("%s", IMAGE("%s"))""" % (item['source_url'], item['preview_url']),
            'Seconds': '',
            'Length': '=INDIRECT(ADDRESS(ROW(), COLUMN()-1))/(60*60*24)',
        }
        seen_key = get_seen_key(pretty_data)
        if seen_key in seen:
            # we've reached a video we processed in a previous run, so stop
            print("breaking for seen_key of " + seen_key) # debug
            break
        new_videos.append(
            [
                pretty_data['Datetime'],
                pretty_data['Leg'],
                pretty_data['Team'],
                pretty_data['OBR'],
                pretty_data['Video'],
                pretty_data['Seconds'],
                pretty_data['Length'],
            ],
        )

    # write incremental_videos as new rows in the Google spreadsheet
    body = { 'values': new_videos }
    result = SHEETS.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Raw Content',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()

    # get the SHEET_ID of sheet 0
    result = SHEETS.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    SHEET_ID = result['sheets'][0]['properties']['sheetId']

    requests = [
        # tidy up the sheet: sort by Datetime (descending):
        {
            'sortRange': {
                'range': {
                    'sheetId': SHEET_ID,
                    'startRowIndex': 1,
                },
                'sortSpecs': [
                    {
                        'dimensionIndex': 0,
                        'sortOrder': 'DESCENDING',
                    },
                ],
            },

        },
        # ...and copy the format of row 100 to the whole sheet (to get the
        # new rows formatted properly)
        {
            'copyPaste': {
                'source': {
                    'sheetId': SHEET_ID,
                    'startRowIndex': 99,
                    'endRowIndex': 100,
                },
                'destination': {
                    'sheetId': SHEET_ID,
                    'startRowIndex': 1,
                },
                'pasteType': 'PASTE_FORMAT',
                'pasteOrientation': 'NORMAL',
            },
        },
    ]

    body = { 'requests': requests }
    result = SHEETS.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID, body=body).execute()

def process_item(raw_item):
    item = {}
    item['datetime'] = raw_item['date']
    item['vor_url'] = raw_item['url']

    class_tags = raw_item['class'].split()
    item['leg'] = class_tags[0]
    item['type'] = class_tags[1]
    item['team'] = class_tags[2]

    if item['type'] == 'social':
        item = process_social_item(raw_item, item)
    elif item['type'] == 'photo':
        item = process_photo_item(raw_item, item)
    elif item['type'] == 'video':
        item = process_video_item(raw_item, item)
    else:
        raise ValueError('Unable to determine item type for item: ' + str(raw_item))

    return item

def process_video_item(raw_item, item):
    item['preview_url'] = raw_item['mediaVideo']['SD']['thumbnails']
    item['source_url'] = raw_item['mediaVideo']['HD']['video']
    return item

def process_social_item(raw_item, item):
    return item

def process_photo_item(raw_item, item):
    return item

def read_full_spreadsheet():
    all_videos = []
    result = SHEETS.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range='Raw Content'
    ).execute()
    values = result.get('values', [])
    headers = values.pop(0)
    for row in values:
        all_videos.append(dict(zip(headers, row)))
    return all_videos

def get_seen_key(item):
    return(item['Datetime'] + item['Leg'] + item['Team'])

def get_pretty_fieldnames():
    return ['Datetime', 'Leg', 'Team', 'OBR', 'Video', 'Seconds', 'Length', 'People', 'Description', 'Tags']

main()


'''
JSON FILE PHOTO ITEM:

      {
        "id": "2613",
        "class": "leg-02 photo team-akzonobel",
        "subsection": "team AkzoNobel",
        "category": "",
        "date": "2017-11-18 01:34:00",
        "title": "13_02_171118_AZN_JSB_00034.jpg",
        "short_text": "",
        "text": "Latest video from team AkzoNobel at 18\/11\/2017 01:34 UTC<br>Watch it now!",
        "social": "",
        "blank": "",
        "main": "1",
        "caption": "Leg 02, Lisbon to Cape Town, day 14,  on board AkzoNobel.  Martine Grael Peter van Niekerk keep one eye for the meteor shower. Photo by James Blake\/Volvo Ocean Race. 18 November, 2017.",
        "author": "James Blake\/Volvo Ocean Race",
        "url": "http:\/\/www.volvooceanrace.com\/en\/raw\/2613.html",
        "media": "https:\/\/www.volvooceanrace.com\/static\/assets\/2017-18\/cropped\/1071\/m107003_crop110015_800x800_proportional_1510968909CE74.jpg",
        "mediaMobile": "https:\/\/www.volvooceanrace.com\/static\/assets\/2017-18\/cropped\/1071\/m107003_crop110015_800x800_proportional_1510968909CE74.jpg",
        "mediaFirst": "https:\/\/www.volvooceanrace.com\/static\/assets\/2017-18\/cropped\/1071\/m107003_crop110015_800x800_proportional_1510968909CE74.jpg",
        "mediaExtra": "https:\/\/www.volvooceanrace.com\/static\/assets\/2017-18\/cropped\/1071\/m107003_crop110015_800x800_proportional_1510968909CE74.jpg"
      },

JSON FILE VIDEO ITEM:

      {
        "id": "2598",
        "class": "leg-02 video dongfeng-race-team",
        "subsection": "Dongfeng Race Team",
        "category": "",
        "date": "2017-11-17 21:01:27",
        "title": "13_02_171117_DFG_JRL_00005.mp4",
        "short_text": "",
        "text": "Latest video from Dongfeng Race Team at 17\/11\/2017 21:01 UTC<br>Watch it now!",
        "social": "",
        "blank": "",
        "main": "1",
        "caption": "",
        "author": "",
        "url": "http:\/\/www.volvooceanrace.com\/en\/raw\/2598.html",
        "media": "http:\/\/www.volvooceanracce.com\/media\/videos\/thumb\/m106988_13-02-171117-dfg-jrl-00005.mp4.png",
        "mediaMobile": "http:\/\/www.volvooceanracce.com\/media\/videos\/thumb\/m106988_13-02-171117-dfg-jrl-00005.mp4.png",
        "mediaFirst": [

        ],
        "mediaExtra": "http:\/\/www.volvooceanracce.com\/media\/videos\/thumb\/m106988_13-02-171117-dfg-jrl-00005.mp4.png",
        "mediaVideo": {
          "SD": {
            "video": "https:\/\/volvooceanrace-2017-18.s3.amazonaws.com\/videos\/cropped\/m106988_13-02-171117-dfg-jrl-00005_SD.mp4",
            "thumbnails": "https:\/\/volvooceanrace-2017-18.s3.amazonaws.com\/videos\/cropped\/thumb\/m106988_13-02-171117-dfg-jrl-00005_00002_480x270.jpg"
          },
          "HD": {
            "video": "https:\/\/volvooceanrace-2017-18.s3.amazonaws.com\/videos\/cropped\/m106988_13-02-171117-dfg-jrl-00005_HD.mp4",
            "thumbnails": "https:\/\/volvooceanrace-2017-18.s3.amazonaws.com\/videos\/cropped\/thumb\/m106988_13-02-171117-dfg-jrl-00005_00002_1280x720.jpg"
          }
        }
      },

JSON FILE SOCIAL ITEM:

      {
        "id": "2597",
        "class": "leg-02 social turn-the-tide-on-plastic",
        "subsection": "Turn the Tide on Plastic",
        "category": "",
        "date": "2017-11-17 20:45:05",
        "title": "The battle is on and we just can't shake them as we try to catch up with the rest of the fleet  #Turnthetideonplastic #Volvooceanrace #Cleanseas #mirpurifoundation #oceanhero #skyoceanrescue #sailing #yachting #betterworkstories #livingthedream #kiwi",
        "short_text": "",
        "text": "Latest video from Turn the Tide on Plastic at 17\/11\/2017 20:45 UTC<br>Watch it now!",
        "social": "<blockquote class=\"instagram-media\" data-instgrm-captioned data-instgrm-version=\"7\" style=\" background:#FFF; border:0; border-radius:3px; box-shadow:0 0 1px 0 rgba(0,0,0,0.5),0 1px 10px 0 rgba(0,0,0,0.15); margin: 1px; max-width:658px; padding:0; width:99.375%; width:-webkit-calc(100% - 2px); width:calc(100% - 2px);\"><div style=\"padding:8px;\"> <div style=\" background:#F8F8F8; line-height:0; margin-top:40px; padding:37.53315649867374% 0; text-align:center; width:100%;\"> <div style=\" background:url(data:image\/png;base64,iVBORw0KGgoAAAANSUhEUgAAACwAAAAsCAMAAAApWqozAAAABGdBTUEAALGPC\/xhBQAAAAFzUkdCAK7OHOkAAAAMUExURczMzPf399fX1+bm5mzY9AMAAADiSURBVDjLvZXbEsMgCES5\/P8\/t9FuRVCRmU73JWlzosgSIIZURCjo\/ad+EQJJB4Hv8BFt+IDpQoCx1wjOSBFhh2XssxEIYn3ulI\/6MNReE07UIWJEv8UEOWDS88LY97kqyTliJKKtuYBbruAyVh5wOHiXmpi5we58Ek028czwyuQdLKPG1Bkb4NnM+VeAnfHqn1k4+GPT6uGQcvu2h2OVuIf\/gWUFyy8OWEpdyZSa3aVCqpVoVvzZZ2VTnn2wU8qzVjDDetO90GSy9mVLqtgYSy231MxrY6I2gGqjrTY0L8fxCxfCBbhWrsYYAAAAAElFTkSuQmCC); display:block; height:44px; margin:0 auto -44px; position:relative; top:-22px; width:44px;\"><\/div><\/div> <p style=\" margin:8px 0 0 0; padding:0 4px;\"> <a href=\"https:\/\/www.instagram.com\/p\/BbnDhtcFgJl\/\" style=\" color:#000; font-family:Arial,sans-serif; font-size:14px; font-style:normal; font-weight:normal; line-height:17px; text-decoration:none; word-wrap:break-word;\" target=\"_blank\">The battle is on and we just can&#39;t shake them as we try to catch up with the rest of the fleet  #Turnthetideonplastic #Volvooceanrace #Cleanseas #mirpurifoundation #oceanhero #skyoceanrescue #sailing #yachting #betterworkstories #livingthedream #kiwi<\/a><\/p> <p style=\" color:#c9c8cd; font-family:Arial,sans-serif; font-size:14px; line-height:17px; margin-bottom:0; margin-top:8px; overflow:hidden; padding:8px 0 7px; text-align:center; text-overflow:ellipsis; white-space:nowrap;\">A post shared by Bianca Cook (@bianca.cooknz) on <time style=\" font-family:Arial,sans-serif; font-size:14px; line-height:17px;\" datetime=\"2017-11-17T20:45:05+00:00\">Nov 17, 2017 at 12:45pm PST<\/time><\/p><\/div><\/blockquote>\n<script async defer src=\"\/\/platform.instagram.com\/en_US\/embeds.js\"><\/script>",
        "blank": "",
        "main": "1",
        "caption": "",
        "author": "",
        "url": "http:\/\/www.volvooceanrace.com\/en\/raw\/2597.html",
        "media": [

        ],
        "mediaMobile": [

        ],
        "mediaFirst": [

        ]
      },
'''
