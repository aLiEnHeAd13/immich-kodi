import json
import sys
from datetime import datetime

import xbmc
import xbmcgui
import xbmcplugin

import iso8601
from models import Album, ItemAsset
from utils import (
    API_KEY,
    RAW_SERVER_URL,
    SHARED_ONLY,
    conn,
    get_asset_name,
    get_url,
    getThumbUrl,
    search_assets,
)

HANDLE = int(sys.argv[1])


def list_albums():
    headers = {
        "Accept": "application/json",
        "User-agent": xbmc.getUserAgent(),
        "x-api-key": API_KEY,
    }
    conn.request("GET", "/api/albums", "", headers)
    res = json.loads(conn.getresponse().read().decode("utf-8"))
    res = [Album.from_api_response(i) for i in res]

    items = [
        (get_url(action="album", id=album.id), xbmcgui.ListItem(album.albumName), True)
        for album in res
    ]
    for item, album in zip(items, res):
        if album.startDate:
            item[1].setDateTime(
                iso8601.parse_date(album.startDate).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
        if album.albumThumbnailAssetId:
            item[1].setArt({"thumb": getThumbUrl(album.albumThumbnailAssetId)})
    xbmcplugin.addSortMethod(HANDLE, sortMethod=xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.addSortMethod(HANDLE, sortMethod=xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.addDirectoryItems(HANDLE, items, len(items))
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)


def album(id):
    xbmcplugin.setContent(HANDLE, "images")

    try:
        assets = search_assets(albumIds=[id])
    except Exception as e:
        xbmc.log("plugin.video.immich: album() failed: %s" % e, xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Immich", str(e), xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(HANDLE, succeeded=False)
        return
    res = [ItemAsset.from_api_response(i) for i in assets]

    items = []
    for asset in res:
        when = (
            asset.exifInfo.dateTimeOriginal
            or asset.fileModifiedAt
            or asset.fileCreatedAt
            or asset.localDateTime
        )
        li = xbmcgui.ListItem(get_asset_name(asset))
        li.setArt({"thumb": getThumbUrl(asset.id)})
        if asset.originalMimeType:
            li.setProperty("MimeType", asset.originalMimeType)
        if when:
            li.setDateTime(iso8601.parse_date(when).strftime("%Y-%m-%dT%H:%M:%S%z"))
        items.append(
            (f"{RAW_SERVER_URL}/api/assets/{asset.id}/original|x-api-key={API_KEY}", li, False)
        )
    xbmcplugin.addDirectoryItems(HANDLE, items, len(items))
    xbmcplugin.addSortMethod(HANDLE, sortMethod=xbmcplugin.SORT_METHOD_DATE)
    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
