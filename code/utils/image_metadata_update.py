"""Take a dictionary of team IDs and RGB colour codes and write the RGB colour as metadata"""
import os
from PIL import Image, PngImagePlugin

premier_league_colours_25_26 = {
     1: '#e20814',
     2: '#91beea',
     3: '#690039',
     4: '#ca0b17',
     5: '#b60501',
     6: '#004a9b',
     7: '#021581',
     8: '#004b97',
     9: '#024593',
    10: '#282624',
    11: "#ffdf1a",
    12: '#b30011',
    13: '#b1d4fa',
    14: '#dc1116',
    15: '#0d0805',
    16: '#f4031c',
    17: '#d20911',
    18: '#152055',
    19: '#7d2d3f',
    20: '#feb906'
}

championship_colours_25_26 = {
    332:  '#183b90',
    59:   '#009ee0',
    387:  '#e21a23',
    348:  '#ec4040',
    1076: '#009edc',
    342:  '#8d8d8d',
    322:  '#f18a01',
    349:  '#3a64a3',
    338:  '#0053a0',
    343:  '#e40f1b',
    384:  '#00367a',
    68:   '#00a650',
    1082: '#fff500',
    325:  '#323c9c',
    1081: '#0799d5',
    69:   '#1a59a3',
    356:  '#ee2227',
    345:  '#4681cf',
    340:  '#ee1338',
    70:   '#e1393e',
    72:   '#030303',
    346:  '#fff002',
    74:   '#173675',
    404:  '#007b4d',
}


def add_image_metadata(id_colour_dict: dict[int, str], league: str):
    """Add metadata to images"""
    os.makedirs("metadata_update", exist_ok=True)

    for team, colour in id_colour_dict.items():
        im = Image.open(f"Logos/{league}/{team}.png")
        meta = PngImagePlugin.PngInfo()
        meta.add_text("primary_color", colour)
        im.save(f"metadata_update/{league}/{team}.png", pnginfo=meta)



def read_image_metadata(id_colour_dict: dict[int, str], league: str):
    """Verify image metadata has successfully been updated"""
    for team, _colour in id_colour_dict.items():
        im = Image.open(f"metadata_update/{league}/{team}.png")
        parsed_colour = im.info.get("primary_color")
        print(f'Team ID {team} with colour {parsed_colour}')
