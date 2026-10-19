import json
import sys
from datetime import datetime, timedelta

import xbmc
import xbmcgui
import xbmcplugin

import iso8601
from models import ItemAsset, TimeBucket, TimelineBucket
from utils import (
    API_KEY,
    conn,
    datelong,
    get_asset_name,
    get_playback,
    get_url,
    getThumbUrl,
    search_assets,
    strftime_polyfill,
)

HANDLE = int(sys.argv[1])


def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + timedelta(days=4)
    return next_month - timedelta(days=next_month.day)


def get_asset_info(id):
    headers = {
        "Accept": "application/json",
        "User-agent": xbmc.getUserAgent(),
        "x-api-key": API_KEY,
    }
    conn.request("GET", "/api/assets/" + id, "", headers)
    return json.loads(conn.getresponse().read().decode("utf-8"))


def time(id, video):
    xbmcplugin.setContent(HANDLE, "images")

    start = iso8601.parse_date(id).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
    filters = {
        "takenAfter": start.strftime(fmt),
        "takenBefore": nxt.strftime(fmt),
        "visibility": "timeline",
    }
    if video:
        filters["type"] = "VIDEO"

    try:
        assets = search_assets(**filters)
    except Exception as e:
        xbmc.log("plugin.video.immich: time() failed: %s" % e, xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Immich", str(e), xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return

    items = []
    for raw in assets:
        item = ItemAsset.from_api_response(raw)
        if video and item.type == "IMAGE":
            continue
        when = (
            item.exifInfo.dateTimeOriginal
            or item.fileModifiedAt
            or item.fileCreatedAt
            or item.localDateTime
        )
        li = xbmcgui.ListItem(get_asset_name(item))
        li.setArt({"thumb": getThumbUrl(item.id)})
        if item.originalMimeType:
            li.setProperty("MimeType", item.originalMimeType)
        if when:
            li.setDateTime(
                iso8601.parse_date(when).strftime("%Y-%m-%dT%H:%M:%S%z")
            )
        items.append((get_playback(item.id, item.type), li, False))

    xbmcplugin.addDirectoryItems(HANDLE, items, len(items))
    xbmcplugin.addSortMethod(HANDLE, sortMethod=xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def timeline(video):
    video = "1" if video else ""

    headers = {
        "Accept": "application/json",
        "User-agent": xbmc.getUserAgent(),
        "x-api-key": API_KEY,
    }
    conn.request("GET", "/api/timeline/buckets?size=MONTH", "", headers)
    res = json.loads(conn.getresponse().read().decode("utf-8"))
    res = [TimelineBucket.from_api_response(i) for i in res]

    xbmcplugin.setContent(HANDLE, "files")

    items = [
        (
            get_url(action="time", id=i.timeBucket, video=video),
            xbmcgui.ListItem(
                strftime_polyfill(datetime.fromisoformat(i.timeBucket), datelong)
            ),
            True,
        )
        for i in res
    ]
    for item, timeline in zip(items, res):
        item[1].setDateTime(
            last_day_of_month(datetime.fromisoformat(timeline.timeBucket)).strftime(
                "%Y-%m-%dT00:00:00Z"
            )
        )

    xbmcplugin.addDirectoryItems(HANDLE, items, len(items))
    xbmcplugin.addSortMethod(HANDLE, sortMethod=xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
