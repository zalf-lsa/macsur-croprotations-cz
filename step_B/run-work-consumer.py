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
from datetime import datetime, date, timedelta
import dateutil.parser
from collections import defaultdict, OrderedDict
import re
import calendar

import zmq

import monica_io

USER = "stella"
LOCAL_RUN = False

PATHS = {
    "stella": {
        "LOCAL_ARCHIVE_PATH_TO_PROJECT": "Z:/projects/macsur-croprotations-cz/",
    },
    "berg": {
        "LOCAL_ARCHIVE_PATH_TO_PROJECT": "P:/macsur-croprotations-cz/",
    },
    "berg2": {
        "LOCAL_ARCHIVE_PATH_TO_PROJECT": "P:/macsur-croprotations-cz/",
    }
}

def create_output(custom_id, result):

    #conversion/support methods
    def convert_date(mydate):
        def DateTimeFromISO(isodate):
            d = dateutil.parser.parse(isodate)
            return d
        mydate = DateTimeFromISO(mydate)
        return format(mydate, '%Y%j')
    
    def SWC_to_mm(swc_m3, pwp_m3, thickness_m):
        if swc_m3 != "n.a.":
            return max((swc_m3 - pwp_m3), 0) * thickness_m * 1000
        else: #stage not reached
            return "n.a."
    
    def soilN_to_kgha(orgN_kg_m3, NO3_kg_m3, NH4_kg_m3, thickness_m):
        return (orgN_kg_m3 + NO3_kg_m3 + NH4_kg_m3) * thickness_m * 10000

    def crop_id(crop):
        return {
            "barley/spring barley": "SG",
            "maize/silage maize": "SM",
            "rape/winter rape": "WRA",
            "rape/cover": "WRC",
            "wheat/winter wheat": "WW"
        }[crop]

    def calc_DryD1(DryDcycle, DryD2, anthesis):        
        if anthesis != "n.a.":
            return DryDcycle - DryD2
        else: #anthesis not reached
            return "n.a."

    def consolidate_DryD2(DryD2, matur):
        if matur == "n.a.":
            return "n.a." #maturity not reached
        else:
            return DryD2
    
    def hydro_year_data(origSpec):
        is_hydro_year_data = False
        add_to_year = 0        
        if re.search('xxxx-10-01', origSpec):
            is_hydro_year_data = True
            add_to_year = 1
        elif re.search('xxx-09-30', origSpec):
            is_hydro_year_data = True
        return is_hydro_year_data, add_to_year

    def avg_SWC(cum_SWCY1, cum_SWCY2, year):
        timespan = 365
        if calendar.isleap(year):
            timespan = 366
        if cum_SWCY1 == "n.a.":#1961
            timespan = (datetime(1961, 9, 30) - datetime(1961, 1, 1)).days + 1
            cum_SWCY1 = 0
        return (cum_SWCY1 + cum_SWCY2)/timespan
            

    crop_out = []
    hydroyear_out = []

    if len(result.get("data", [])) > 0 and len(result["data"][0].get("results", [])) > 0:

        crop_year_values = defaultdict(lambda: defaultdict(dict))
        hydroyear_values = defaultdict(dict)
        crop_sequence =[]

        for data in result.get("data", []):
            results = data.get("results", [])
            oids = data.get("outputIds", [])

            #skip empty results, e.g. when event condition haven't been met
            if len(results) == 0:
                continue

            assert len(oids) == len(results)            

            hydro_year, add_to_year = hydro_year_data(data["origSpec"])

            for kkk in range(0, len(results[0])):
                vals = {}
                
                if str(data["origSpec"]) == '"crop"': #reference order of the crop rotation
                    crop_sequence.append((results[0][kkk], results[1][kkk]))

                for iii in range(0, len(oids)):
                    oid = oids[iii]
                    val = results[iii][kkk]

                    name = oid["name"] if len(oid["displayName"]) == 0 else oid["displayName"]

                    if isinstance(val, types.ListType):
                        for val_ in val:
                            vals[name] = val_
                    else:
                        vals[name] = val

                if "Year" not in vals:
                    print "Missing Year in result section. Skipping results section."
                    continue
                
                if hydro_year:
                    hydroyear_values[vals.get("Year") + add_to_year].update(vals)
                else:
                    crop_year_values[vals.get("Crop")][vals.get("Year")].update(vals)
        
        for element in crop_sequence:
            vals = crop_year_values[element[0]][element[1]]

            crop_out.append([
                convert_date(vals.get("sowing")),
                vals.get("anthesis", "n.a."),
                vals.get("matur", "n.a."),
                convert_date(vals.get("harv")),
                crop_id(vals.get("Crop")),
                vals.get("yield"),
                vals.get("biomass"),
                vals.get("roots"),
                vals.get("LAImax"),
                vals.get("Nfertil"),
                vals.get("irrig"),
                vals.get("N-uptake"),
                vals.get("Nagb"),
                vals.get("ETcG"),
                vals.get("ETaG"),
                vals.get("TraG"),
                vals.get("PerG"),
                SWC_to_mm(vals.get("SWCS1"), vals.get("Pwp1"), 0.3),
                SWC_to_mm(vals.get("SWCS2"), vals.get("Pwp2"), 1.5),
                SWC_to_mm(vals.get("SWCA1", "n.a."), vals.get("Pwp1"), 0.3),
                SWC_to_mm(vals.get("SWCA2", "n.a."), vals.get("Pwp2"), 1.5),
                SWC_to_mm(vals.get("SWCM1", "n.a."), vals.get("Pwp1"), 0.3),
                SWC_to_mm(vals.get("SWCM2", "n.a."), vals.get("Pwp2"), 1.5),
                soilN_to_kgha(vals.get("OrgN1_kgm3"), vals.get("NO31_kgm3"), vals.get("NH41_kgm3"), 0.3),
                soilN_to_kgha(vals.get("OrgN2_kgm3"), vals.get("NO32_kgm3"), vals.get("NH42_kgm3"), 1.5),
                soilN_to_kgha(0, vals.get("NO31_kgm3"), vals.get("NH41_kgm3"), 0.3),
                soilN_to_kgha(0, vals.get("NO32_kgm3"), vals.get("NH42_kgm3"), 1.5),
                vals.get("NleaG"),
                vals.get("TRRel"),
                vals.get("Reduk"),
                calc_DryD1(vals.get("DryDcycle", 0), vals.get("DryD2", 0), vals.get("anthesis", "n.a.")),
                consolidate_DryD2(vals.get("DryD2", 0), vals.get("matur", "n.a.")),
                vals.get("Nresid"),
            ])
        
        for year in OrderedDict(sorted(hydroyear_values.items())):
            if year == 2081: #don't need it
                continue

            vals = hydroyear_values[year] 
            
            SWC1Y_m3 = avg_SWC(vals.get("SWC1Y1", "n.a."), vals.get("SWC1Y2"), year)
            SWC2Y_m3 = avg_SWC(vals.get("SWC2Y1", "n.a."), vals.get("SWC2Y2"), year)

            hydroyear_out.append([
                year,
                vals.get("ETcY1", 0) + vals.get("ETcY2"), #in 1961 Y1 is missing: 0 as default
                vals.get("ETaY1", 0) + vals.get("ETaY2"),
                vals.get("TraY1", 0) + vals.get("TraY2"),
                vals.get("PerY1", 0) + vals.get("PerY2"),
                SWC_to_mm(SWC1Y_m3, vals.get("Pwp1"), 0.3),
                SWC_to_mm(SWC2Y_m3, vals.get("Pwp2"), 1.5),
                "n.a.", #vals.get("RunoffY1", 0) + vals.get("RunoffY2"),
                vals.get("NleaY1", 0) + vals.get("NleaY2"),
                vals.get("NminY1", 0) + vals.get("NminY2"),
                vals.get("DenitY1", 0) + vals.get("DenitY2"),
                vals.get("VolatY1", 0) + vals.get("VolatY2"),
                vals.get("SOC1_gm2") * 10,
                vals.get("SOC2_gm2") * 10,
            ])

    return crop_out, hydroyear_out


HEADER_CROP = \
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

HEADER_YEAR = \
    "YEAR," \
    "ETcY," \
    "ETaY," \
    "TraY," \
    "PerY," \
    "SWCY1," \
    "SWCY2," \
    "Runoff," \
    "NleaY," \
    "MINY," \
    "DENY," \
    "VOLAT," \
    "SOC1," \
    "SOC2," \
    "\n"


def write_data(custom_id, crp_res, yr_res):
    "write data"
    
    id_info = custom_id.split("|")

    directory = PATHS[USER]["LOCAL_ARCHIVE_PATH_TO_PROJECT"] + "output/" + id_info[1]

    path_to_file_crop = directory + "/" + "C" + id_info[0] + "-" + id_info[3] + "_" + id_info[4] + "_" + id_info[2] + ".csv"
    path_to_file_year = directory + "/" + "Y" + id_info[0] + "-" + id_info[3] + "_" + id_info[4] + "_" + id_info[2] + ".csv"
    
    with open(path_to_file_crop, 'ab') as _:
        writer = csv.writer(_, delimiter=",")
        _.write(HEADER_CROP)
        for row_ in crp_res:
            writer.writerow(row_)

    with open(path_to_file_year, 'ab') as _:
        writer = csv.writer(_, delimiter=",")
        _.write(HEADER_YEAR)
        for row_ in yr_res:
            writer.writerow(row_)

    

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
    
    while not leave:

        try:
            result = socket.recv_json(encoding="latin-1")
        except:            
            continue

        if result["type"] == "finish":
            print "received finish message"
            leave = True

        else:
            print "received work result ", i, " customId: ", result.get("customId", "")

            custom_id = result["customId"]

            crp_res, yr_res = create_output(custom_id, result)
            
            write_data(custom_id, crp_res, yr_res)

            i = i + 1

collector()