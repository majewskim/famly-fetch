#!/usr/bin/env python3

"""Fetch all famly.co pictures of your kid

Auth has two versions:

 - "non-v2" has a `?accessToken=XXX` as a GET-parameter
 - v2-urls demands a `x-famly-accesstoken: XXX` header

"""

import argparse
from datetime import datetime
import os
import shutil
import time
import urllib.request

import piexif
from PIL import Image

from api_client import ApiClient

class FamlyDownloader:
    """Class for downloading images from Famly."""

    def __init__(self, email, password):
        self._pictures_folder = "pictures"
        self.api_client = ApiClient()
        self.api_client.login(email, password)

    def download_images_by_child_id(self, child_id, first_name):
        """Download images by childId"""
        imgs = self.api_client.make_api_request(
            "GET", "/api/v2/images/tagged", params={"childId": child_id}
        )

        print(f"Fetching {len(imgs)} images for {first_name}")

        for img_no, img in enumerate(imgs, start=1):
            print(f" - image {img['imageId']} ({img_no}/{len(imgs)})")

            # This is constructed from very few examples - I might be asking it
            # to crop things it should not...
            url = f"{img['prefix']}{img['height']}{img['width']}{img['key']}"

            # sleep for 1s to avoid 400 errors
            time.sleep(1)

            req = urllib.request.Request(url=url)

            created_at = img["createdAt"]
            captured_date = datetime.fromisoformat(created_at).strftime("%d-%m-%Y-%H-%M-%S")
            captured_date_exif = datetime.fromisoformat(created_at).strftime("%Y:%m:%d %H:%M:%S")

            filename = os.path.join(self._pictures_folder, f"{first_name}-{captured_date}.jpg")

            with urllib.request.urlopen(req) as r, open(filename, "wb") as f:
                if r.status != 200:
                    raise f"B0rked! {r.read().decode('utf-8')}"
                shutil.copyfileobj(r, f)

            # write DateTimeOriginal to the image
            # Load the image
            saved_img = Image.open(filename)

            # Prepare the EXIF data
            exif_dict = {"Exif": {piexif.ExifIFD.DateTimeOriginal: captured_date_exif.encode()}}
            exif_bytes = piexif.dump(exif_dict)

            # Write the EXIF data to the image
            saved_img.save(filename, exif=exif_bytes)



if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Fetch kids' images from famly.co")
    parser.add_argument("email", help="Auth email")
    parser.add_argument("password", help="Auth password")
    args = parser.parse_args()

    # Create the downloader
    famly_downloader = FamlyDownloader(args.email, args.password)

    my_info = famly_downloader.api_client.me_me_me()


    # Current children
    for role in my_info["roles2"]:
        famly_downloader.download_images_by_child_id(role["targetId"], role["title"])

    # Previous children (that's what they call it)
    prev_children = []
    for ele in my_info["behaviors"]:
        if ele["id"] == "ShowPreviousChildren":
            prev_children = ele["payload"]["children"]

    for child in prev_children:
        famly_downloader.download_images_by_child_id(
            child["childId"], child["name"]["firstName"])
