#!/opt/poetry/bin/python

"""
    Shitty bustimes.org API importer lol.

    https://github.com/J0w03L | https://j0w03l.me
"""

import sys
import pg8000
import os
import json
import argparse

stdIn = sys.stdin
stdOut = sys.stdout

parsed = json.loads(stdIn.read())

con = pg8000.connect(
    host = "postgres",
    database = "tb-data",
    user = "postgres",
    password = "postgres",
    port = 5432
)

def parseVehicleTypes():
    types = parsed["results"]
    count = 0

    for vehicleType in types:
        con.run(
            "INSERT INTO vehicles_vehicletype (name, style, fuel) VALUES (:name, :style, :fuel) ON CONFLICT DO NOTHING",
            name = vehicleType["name"],
            style = vehicleType["style"],
            fuel = vehicleType["fuel"]
        )
        count = count + 1

    con.commit()
    print(f"did: {count} vehicle types")

def parseLiverys():
    liverys = parsed["results"]
    count = 0

    for livery in liverys:
        con.run(
            "INSERT INTO vehicles_livery (name, left_css, right_css, white_text, text_colour, stroke_colour, published, show_name, colour, colours, horizontal) VALUES (:name, :left_css, :right_css, :white_text, :text_colour, :stroke_colour, true, true, '', '', false) ON CONFLICT DO NOTHING",
            name = livery["name"],
            left_css = livery["left_css"],
            right_css = livery["right_css"],
            white_text = livery["white_text"],
            text_colour = livery["text_colour"],
            stroke_colour = livery["stroke_colour"]
        )
        count = count + 1

    con.commit()
    print(f"did: {count} liverys")

if __name__ == "__main__":
    #parseVehicleTypes()
    parseLiverys()
