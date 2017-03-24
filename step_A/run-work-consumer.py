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

import sys
import gc
import csv
import types
import os
from datetime import datetime
import dateutil.parser
from collections import defaultdict, OrderedDict

import zmq

import monica_io

LOCAL_RUN = True

def create_output(crop_id, location, result):
    "create crop output lines"

    #conversion methods
    def convert_date(mydate):
        def DateTimeFromISO(isodate):
            d = dateutil.parser.parse(isodate)
            return d
        mydate = DateTimeFromISO(mydate)
        return format(mydate, '%Y%j')
    
    def SWC_to_mm(swc_m3, pwp_m3, thickness_m):
        return max((swc_m3 - pwp_m3), 0) * thickness_m * 1000
    
    def soilN_to_kgha(orgN_kg_m3, NO3_kg_m3, NH4_kg_m3, thickness_m):
        return (orgN_kg_m3 + NO3_kg_m3 + NH4_kg_m3) * thickness_m * 10000

    out = []
    #if crop_id == "SM":
    if len(result.get("data", [])) > 0 and len(result["data"][0].get("results", [])) > 0:

        all_vals = defaultdict(dict)

        for data in result.get("data", []):
            results = data.get("results", [])
            oids = data.get("outputIds", [])

            #skip empty results, e.g. when event condition haven't been met
            if len(results) == 0:
                continue

            assert len(oids) == len(results)

            vals = {}
            for iii in range(0, len(results)):
                oid = oids[iii]
                val = results[iii]

                name = oid["name"] if len(oid["displayName"]) == 0 else oid["displayName"]

                vals[name] = val

            all_vals.update(vals)

    if len(all_vals) > 0:
        
        out.append([
            convert_date(all_vals.get("sowing")[0]),
            all_vals.get("anthesis", "n.a.")[0],
            all_vals.get("matur", "n.a.")[0],
            convert_date(all_vals.get("harv")[0]),
            crop_id,
            all_vals.get("yield")[0],
            all_vals.get("biomass")[0],
            all_vals.get("roots")[0],
            all_vals.get("LAImax")[0],
            all_vals.get("Nfertil", "n.a.")[0],
            all_vals.get("irrig")[0],
            all_vals.get("N-uptake")[0],
            all_vals.get("Nagb")[0],
            all_vals.get("ETcG")[0],
            all_vals.get("ETaG")[0],
            all_vals.get("TraG")[0],
            all_vals.get("PerG")[0][0],
            SWC_to_mm(all_vals.get("SWCS1")[0], all_vals.get("Pwp1")[0], 0.3),
            SWC_to_mm(all_vals.get("SWCS2")[0], all_vals.get("Pwp2")[0], 1.5),
            SWC_to_mm(all_vals.get("SWCA1")[0], all_vals.get("Pwp1")[0], 0.3),
            SWC_to_mm(all_vals.get("SWCA2")[0], all_vals.get("Pwp2")[0], 1.5),
            SWC_to_mm(all_vals.get("SWCM1")[0], all_vals.get("Pwp1")[0], 0.3),
            SWC_to_mm(all_vals.get("SWCM2")[0], all_vals.get("Pwp2")[0], 1.5),
            soilN_to_kgha(all_vals.get("OrgN1_kgm3")[0], all_vals.get("NO31_kgm3")[0], all_vals.get("NH41_kgm3")[0], 0.3),
            soilN_to_kgha(all_vals.get("OrgN2_kgm3")[0], all_vals.get("NO32_kgm3")[0], all_vals.get("NH42_kgm3")[0], 1.5),
            soilN_to_kgha(0, all_vals.get("NO31_kgm3")[0], all_vals.get("NH41_kgm3")[0], 0.3),
            soilN_to_kgha(0, all_vals.get("NO32_kgm3")[0], all_vals.get("NH42_kgm3")[0], 1.5),
            all_vals.get("NleaG")[0],
            all_vals.get("TRRel")[0],
            all_vals.get("Reduk")[0],
            all_vals.get("DryD1", "n.a.")[0],
            all_vals.get("DryD2", "n.a.")[0],
            all_vals.get("Nresid")[0],
        ])

    return out

#+"Stage,HeatRed,RelDev,"\
HEADER = \
    "sowing," \
    "anthesis," \
    "matur," \
    "harv," \
    "crop," \
    "yield," \
    "biomass," \
    "roots," \
    "LAImax," \
    "Nfertil," \
    "irrig," \
    "N-uptake," \
    "Nagb," \
    "ETcG," \
    "ETaG," \
    "TraG," \
    "PerG," \
    "SWCS1," \
    "SWCS2," \
    "SWCA1," \
    "SWCA2," \
    "SWCM1," \
    "SWCM2," \
    "soilN1," \
    "soilN2," \
    "Nmin1," \
    "Nmin2," \
    "NleaG," \
    "TRRel," \
    "Reduk," \
    "DryD1," \
    "DryD2," \
    "Nresid," \
    "\n"


#overwrite_list = set()
def write_data(crop_id, location, data):
    "write data"

    crops = {
        "SB": "Barley",
        "WW": "Wheat",
        "SM": "Maize",
        "WR": "Rape"
    }

    current_dir = os.getcwd()
    path_to_file = current_dir + "/step_A/out/" + crops[crop_id] + "/" + location + ".csv"

    if not os.path.isfile(path_to_file):
        with open(path_to_file, "w") as _:
            _.write(HEADER)
        
    with open(path_to_file, 'ab') as _:
        writer = csv.writer(_, delimiter=",")
        for row_ in data[(crop_id, location)]:
            writer.writerow(row_)
        data[(crop_id, location)] = []


def collector():
    "collect data from workers"

    data = defaultdict(list)

    i = 1
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    if LOCAL_RUN:
        socket.connect("tcp://localhost:7777")
    else:
        socket.connect("tcp://cluster2:7777")
    socket.RCVTIMEO = 1000
    leave = False
    write_normal_output_files = False
    start_writing_lines_threshold = 10
    
    while not leave:

        try:
            result = socket.recv_json(encoding="latin-1")
        except:
            for crop_id, location in data.keys():
                if len(data[(crop_id, location)]) > 0:
                    write_data(crop_id, location, data)
            continue

        if result["type"] == "finish":
            print "received finish message"
            leave = True

        elif not write_normal_output_files:
            print "received work result ", i, " customId: ", result.get("customId", "")

            custom_id = result["customId"]
            crop_id = custom_id.split("_")[0]
            location = "C" + custom_id.split("_")[2]
            harvest_year = custom_id.split("_")[-1:]

            res = create_output(crop_id, location, result)
            data[(crop_id, location)].extend(res)

            if len(data[(crop_id, location)]) >= start_writing_lines_threshold:
                write_data(crop_id, location, data)

            i = i + 1

        elif write_normal_output_files:
            print "received work result ", i, " customId: ", result.get("customId", "")

            custom_id = result["customId"]
            crop_id = custom_id.split("_")[0]
            location = "C" + custom_id.split("_")[2]
            harvest_year = custom_id.split("_")[-1:]
            

            #with open("out/out-" + str(i) + ".csv", 'wb') as _:
            with open("step_A/out/out-" + custom_id + ".csv", 'wb') as _:
                writer = csv.writer(_, delimiter=",")

                for data_ in result.get("data", []):
                    results = data_.get("results", [])
                    orig_spec = data_.get("origSpec", "")
                    output_ids = data_.get("outputIds", [])

                    if len(results) > 0:
                        writer.writerow([orig_spec.replace("\"", "")])
                        for row in monica_io.write_output_header_rows(output_ids,
                                                                        include_header_row=True,
                                                                        include_units_row=True,
                                                                        include_time_agg=False):
                            writer.writerow(row)

                        for row in monica_io.write_output(output_ids, results):
                            writer.writerow(row)

                    writer.writerow([])

            i = i + 1

collector()