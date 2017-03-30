import os
import csv
from datetime import date
from datetime import timedelta
import json
import copy

def generate_rotations(basepath):
    all_crops = basepath + "step_B//templates//all_crops.json"

    with open(all_crops) as all_crops:    
        all_crops = json.load(all_crops)

    rotation_1_main =[("WW_1", "01"), ("SB_1", "02"), ("SM_NoMan", "03"), ("WW_1", "04"), ("WR", "05")]
    rotation_2_main =[("WW", "06"), ("SB", "07"), ("SM", "08"), ("WW", "09"), ("WR", "10")]
    insert_catch_before_it = ["SB", "SM"]

    def rotate(rotation):
        last = rotation.pop()
        rotation = [last] + rotation
        return rotation

    def next_crop(rotation, index):
        if index == len(rotation) - 1:
            next_crp = rotation[0][0]
            next_index = 0
        else:
            next_crp = rotation[index + 1][0]
            next_index = index + 1
        return next_crp, next_index

    def create_cultivation_method(year, crop_info):
        cultivation_method = {"worksteps": []}
        added_year = False
        if "is-cover-crop" in crop_info:
            cultivation_method["is-cover-crop"] = crop_info["is-cover-crop"]
        if "can-be-skipped" in crop_info:
            cultivation_method["can-be-skipped"] = crop_info["can-be-skipped"]
        for step in crop_info["worksteps"]:
            mystep = copy.deepcopy(step)
            for k,v in mystep.iteritems():
                if "0000-" in str(v):
                    mystep[k] = v.replace("0000", str(year))
                if "0001-" in str(v):
                    if not added_year: year +=1
                    added_year = True
                    mystep[k] = v.replace("0001", str(year))
            cultivation_method["worksteps"].append(mystep)
        return year, cultivation_method

    rotations = {}

    for element in range(len(rotation_1_main)):
        current_year = 1961
        current_index = -1 #identifies current crop

        rot_1_name = rotation_1_main[0][1]
        rot_2_name = rotation_2_main[0][1]

        rotation_1 = []
        rotation_2 = []  #rotation 2 does not need absolute dates, it's done only for consistency
        
        while current_year <= 1990: #spinup phase, common for 1st and 2nd rotation

            crop_in_rotation, current_index = next_crop(rotation_2_main, current_index)

            if crop_in_rotation in insert_catch_before_it:
                current_year, cultivation_method_cc = create_cultivation_method(current_year, all_crops["WRC"])
                rotation_1.append(cultivation_method_cc)
                rotation_2.append(cultivation_method_cc)

            current_year, cultivation_method = create_cultivation_method(current_year, all_crops[crop_in_rotation])

            rotation_1.append(cultivation_method)
            rotation_2.append(cultivation_method)

        while current_year <= 2080: #run phase, 2 distinct crop rotations

            crop_in_2nd_rotation, ignore_this_index = next_crop(rotation_2_main, current_index) #ignore this index to avoid double counting
            crop_in_1st_rotation, current_index = next_crop(rotation_1_main, current_index)        

            if crop_in_2nd_rotation in insert_catch_before_it:
                current_year, cultivation_method_cc = create_cultivation_method(current_year, all_crops["WRC"])
                rotation_2.append(cultivation_method_cc)
            
            ignore_this_year, cultivation_method = create_cultivation_method(current_year, all_crops[crop_in_1st_rotation]) #ignore this year to avoid double counting
            rotation_1.append(cultivation_method)

            current_year, cultivation_method = create_cultivation_method(current_year, all_crops[crop_in_2nd_rotation])
            rotation_2.append(cultivation_method)

        rotations[rot_1_name] = rotation_1 #store rotations
        rotations[rot_2_name] = rotation_2

        rotation_1_main = rotate(rotation_1_main)
        rotation_2_main = rotate(rotation_2_main)
    
    return rotations
