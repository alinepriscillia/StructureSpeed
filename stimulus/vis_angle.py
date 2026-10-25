# Run in eelbrain environment as upgrade to Pillow 10 removed the getsize function. Eelbrain environment has Pillow 9.5.
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import pandas as pd
from pathlib import Path
import os
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from project_config import get_path

# set path
ROOT = get_path("stimuli")
sdir = get_path("visual_angle")

# Sets the path for all of the relevant stim
scrambled_story2_path = ROOT / "story2_scrambled.csv"
scrambled_story3_path = ROOT / "story3_scrambled.csv"
intact_story2_path = ROOT / "story2_final_stim.csv"
intact_story3_path = ROOT / "story3_final_stim.csv"

##### CODE EXECUTED AT THE BOTTOM #######


def get_vis_angle(stim, row, col, font):
    # get rid of extra spaces:
    clear = 0
    while clear == 0:
        if stim[-1] == " ":
            stim = stim[:-1]
        else:
            clear = 1
    # load in background
    img = Image.open(ROOT / "Background.png")

    # draw it
    I1 = ImageDraw.Draw(img)

    # set font size and width and height
    myfont = ImageFont.truetype(font, 20)

    #pixels per sentence (spx), stim height (sheight)
    spx, sheight = myfont.getsize(stim)  # creates tuple

    # Get width and height of background image: THESE MATCH THE PROJECTOR DISPLAY RESOLUTION
    width, height = img.size

    #get pix/cm on projector screen (24cm)
    pxc = width / 24

    #vis angle per cm = 1.3021 (at average 44cm eye to screen distance)(https://elvers.us/perception/visualAngle/)
    ## if you really want, you could measure distance from back of each subj's head to the surface of their eye
    ## and subtract that from MEG helmet-base(H) to screen(S) distance such that line HS intersects the position
    ## of their eye in the helmet
    ## and average over every subject and recalculate average deg/cm after you collect all of your data,
    ## but..... it'll be 44 for most people
    dcm = 1.3

    #pixels per degree
    pxd = pxc / dcm

    #degrees per sentence: pixels in sentence / pixels per degree (rounded)
    stim_deg = spx / pxd
    stim_deg = round(stim_deg, 3)

    return stim_deg


def get_word_angle(word, font):

    # load in background
    img = Image.open(ROOT / "Background.png")

    # draw it
    I1 = ImageDraw.Draw(img)

    # set font size and width and height
    myfont = ImageFont.truetype(font, 20)

    #pixels per word (wpx)
    wpx, sheight = myfont.getsize(word)  # creates tuple

    # Get width and height of background image: THESE MATCH THE PROJECTOR DISPLAY RESOLUTION
    width, height = img.size

    #get pix/cm on projector screen
    pxc = width / 24

    #vis angle per cm = 1.3021 (at average 44cm eye to screen distance)
    #if you really want..... and so on
    dcm = 1.3

    #pixels per degree
    pxd = pxc / dcm

    #degrees per word: pixels in word / pixels per degree (rounded)
    word_deg = wpx / pxd
    word_deg = round(word_deg, 3)

    return word_deg


################################################################################
################################# RUN THE CODE #################################
################################################################################

def main():
    """Calculate visual angles for the configured stimulus tables."""
    # load stimuli (note the special file since æ, ø, and å don't work)
    stim_table = {
        "scrambled_story2": pd.read_csv(scrambled_story2_path),
        "scrambled_story3": pd.read_csv(scrambled_story3_path),
        "intact_story2": pd.read_csv(intact_story2_path),
        "intact_story3": pd.read_csv(intact_story3_path),
    }

    #full sentences
    for cond, stimuli in stim_table.items():
        stim_list = []
        deg_list = []
        for idx, row in stimuli.iterrows():
            col = "chunk"  # name of column with stimuli you want to get angles for
            stim = row[col]
            stim_deg = get_vis_angle(stim, row, col, font= "Futura")
            stim_list.append(stim)
            deg_list.append(stim_deg)

        df = pd.DataFrame(list(zip(stim_list, deg_list)), columns=["stim", "deg"])

        df.to_csv(sdir / f"{cond}_stim_degrees.csv")


if __name__ == "__main__":
    main()
