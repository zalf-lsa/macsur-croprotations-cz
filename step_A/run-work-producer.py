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
import os
import math
import json
import csv
from StringIO import StringIO
from datetime import date, datetime, timedelta
from collections import defaultdict
import sys
import zmq
import monica_io

USER = "stella"
LOCAL_RUN = True

PATHS = {
    "stella": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/stella/Documents/GitHub",        
    },
    "berg": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/berg.ZALF-AD.000/Documents/GitHub",
    },
    "berg2": {
        "INCLUDE_FILE_BASE_PATH": "C:/Users/berg.ZALF-AD/GitHub",
    }    
}

sim_files_path = PATHS[USER]["INCLUDE_FILE_BASE_PATH"] + "/macsur-croprotations-cz/step_A/sim_files/"
crop_files_path = PATHS[USER]["INCLUDE_FILE_BASE_PATH"] + "/macsur-croprotations-cz/step_A/crop_files/"
climate_files_path = PATHS[USER]["INCLUDE_FILE_BASE_PATH"] + "/macsur-croprotations-cz/step_A/climate_files/"
site_files_path = PATHS[USER]["INCLUDE_FILE_BASE_PATH"] + "/macsur-croprotations-cz/step_A/site_files/"

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

    path_out_stepA = PATHS[USER]["INCLUDE_FILE_BASE_PATH"] + "/macsur-croprotations-cz/step_A/out_stepA.json"
    with open(path_out_stepA) as _:
        out_stepA = json.load(_)

    i=1
    start_store = time.clock()

    for filename in os.listdir(sim_files_path):
        current_sim = filename[4:]
        crop_id = current_sim.split("_")[0]
        location = current_sim.split("_")[2].lower()

        sim_file = sim_files_path + filename
        crop_file = crop_files_path + "crop_" + current_sim
        site_file = site_files_path + location + ".json"
        climate_file = climate_files_path + location + ".csv"

        with open(sim_file) as _:
            sim = json.load(_)
            sim["crop.json"] = crop_file #maybe this is not needed (assigned below)
            sim["site.json"] = site_file #maybe this is not needed (assigned below)
            sim["climate.csv"] = climate_file
            sim["include-file-base-path"] = PATHS[USER]["INCLUDE_FILE_BASE_PATH"]

        with open(crop_file) as _:
            crop = json.load(_)

        with open(site_file) as _:
            site = json.load(_)

        env = monica_io.create_env_json_from_json_config({
            "crop": crop,
            "site": site,
            "sim": sim
            })

        monica_io.add_climate_data_to_env(env, sim)

        env["events"] = out_stepA["output"][crop_id]

        env["customId"] = current_sim.split(".")[0]

        socket.send_json(env)
        print "sent env ", i, " customId: ", env["customId"]
        i += 1


    stop_store = time.clock()

    print "sending ", (i-1), " envs took ", (stop_store - start_store), " seconds"
    return


main()