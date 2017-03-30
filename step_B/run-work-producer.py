#!/usr/bin/python
# -*- coding: UTF-8

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/. */

# Authors:
# Michael Berg-Mohnicke <michael.berg@zalf.de>
# Tommaso Stella <tommaso.stella@zalf.de>
#
# Maintainers:
# Currently maintained by the authors.
#
# This file has been created at the Institute of
# Landscape Systems Analysis at the ZALF.
# Copyright (C: Leibniz Centre for Agricultural Landscape Research (ZALF)

import time
import json
import copy
from datetime import date, datetime, timedelta
from collections import defaultdict
import sys
import zmq
import monica_io
import rotate_script

USER = "stella"
LOCAL_RUN = True

PATHS = {
    "stella": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/stella/Documents/GitHub",
        "LOCAL_ARCHIVE_PATH_TO_PROJECT": "Z:/projects/macsur-croprotations-cz/",
        "ARCHIVE_PATH_TO_PROJECT": "/archiv-daten/md/projects/macsur-croprotations-cz/"
    },
    "berg": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/berg.ZALF-AD.000/Documents/GitHub",
        "LOCAL_ARCHIVE_PATH_TO_PROJECT": "P:/macsur-croprotations-cz/",
        "ARCHIVE_PATH_TO_PROJECT": "/archiv-daten/md/projects/macsur-croprotations-cz/"
    },
    "berg2": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/berg.ZALF-AD/GitHub",
        "LOCAL_ARCHIVE_PATH_TO_PROJECT": "P:/macsur-croprotations-cz/",
        "ARCHIVE_PATH_TO_PROJECT": "/archiv-daten/md/projects/macsur-croprotations-cz/"
    }
}


def main():
    "main"

    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    config = {
        "port": 6666
    }
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            k,v = arg.split("=")
            if k in config:
                config[k] = int(v)

    if LOCAL_RUN:
        socket.connect("tcp://localhost:" + str(config["port"]))
    else:
        socket.connect("tcp://cluster2:" + str(config["port"]))

    base_path = PATHS[USER]["INCLUDE_FILE_BASE_PATH"]
    with open(base_path + "/macsur-croprotations-cz/step_B/templates/out_stepB.json") as _:
        out_stepB = json.load(_)

    with open(base_path + "/macsur-croprotations-cz/step_B/templates/crop_template.json") as _:
        crop_template = json.load(_)

    with open(base_path + "/macsur-croprotations-cz/step_B/templates/sim_template.json") as _:
        sim_template = json.load(_)
    
    sites = {}
    with open(base_path + "/macsur-croprotations-cz/step_B/soils/good_soil.json") as _:
        sites["good_soil"] = json.load(_)
    with open(base_path + "/macsur-croprotations-cz/step_B/soils/poor_soil.json") as _:
        sites["poor_soil"] = json.load(_)

    sim = sim_template
    sim["output"]["events"] = out_stepB["my_out"]

    #with open("test.json", 'w') as testfile:
    #    json.dump(sim, testfile)

    stations = ["LED", "VER", "DOM"]

    soils = ["good_soil", "poor_soil"]

    rotations = rotate_script.generate_rotations(PATHS[USER]["INCLUDE_FILE_BASE_PATH"] + "//macsur-croprotations-cz//")

    climate_data = [
        "naw",
        "now",
        "MRI-CGCM3",
        "IPSL-CM5A-MR",
        "HADGEM2-ES",
        "CNRM-CM5",
        "BNU-ESM"
    ]

    site_parameters = {
        "LED": {
            "Latitude": 48.8,
            "NDeposition": 33
        },
        "VER": {
            "Latitude": 49.5,
            "NDeposition": 15
        },
        "DOM": {
            "Latitude": 49.5,
            "NDeposition": 40
        }
    }

    counter=1
    start_store = time.clock()

    def generate_and_send_env(station, soil_type, rot_id, climate, realization, counter):
        
        def limit_rootdepth():
            for cultivation_method in env["cropRotation"]:
                for workstep in cultivation_method["worksteps"]:
                    if workstep["type"] == "Seed":
                        current_rootdepth = float(workstep["crop"]["cropParams"]["cultivar"]["CropSpecificMaxRootingDepth"])
                        workstep["crop"]["cropParams"]["cultivar"]["CropSpecificMaxRootingDepth"] = min(current_rootdepth, 0.8)
                        break
                
        crop = copy.deepcopy(crop_template)
        crop["cropRotation"] += rotations[rot_id]
        
        site = sites[soil_type]
        site["SiteParameters"]["Latitude"] = site_parameters[station]["Latitude"]
        site["SiteParameters"]["NDeposition"] = site_parameters[station]["NDeposition"]

        #with open("crop_test.json", 'w') as testfile:
        #    json.dump(crop, testfile)
        
        #with open("sim_test.json", 'w') as testfile:
        #    json.dump(sim, testfile)
        
        #with open("site_test.json", 'w') as testfile:
        #    json.dump(site, testfile)

        env = monica_io.create_env_json_from_json_config({
            "crop": crop,
            "site": site,
            "sim": sim
            })
        
        env["csvViaHeaderOptions"] = sim["climate.csv-options"]
        if soil_type == "poor_soil":
            limit_rootdepth()
        
        weather_file_name = station + "-" + climate
        if climate != "now" and climate != "naw":
            weather_file_name += "-RCP85"
        weather_file_name += "_" + str(realization).zfill(2) + ".csv"

        if LOCAL_RUN:
            env["pathToClimateCSV"] = PATHS[USER]["LOCAL_ARCHIVE_PATH_TO_PROJECT"] + "weather/converted/no_snow_cover_assumed/" + weather_file_name
        else:
            env["pathToClimateCSV"] = PATHS[USER]["ARCHIVE_PATH_TO_PROJECT"] + "weather/converted/no_snow_cover_assumed/" + weather_file_name 
        
        env["customId"] = station + "|" + soil + "|" + rotation_id + "|" + climate + "|" + str(realization)

        socket.send_json(env)
        print "sent env ", counter, " customId: ", env["customId"]
        return counter + 1

    for station in stations:
        for soil in soils:
            for rotation_id in rotations:
                for climate in climate_data:
                    for realization in range(1, 11):
                        counter = generate_and_send_env(station, soil, rotation_id, climate, realization, counter)

    stop_store = time.clock()

    print "sending ", (counter-1), " envs took ", (stop_store - start_store), " seconds"
    return


main()