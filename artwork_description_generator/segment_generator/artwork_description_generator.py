import math
import json
import copy
import os.path
import sys
import argparse 


if __name__ == "__main__":
    rings = 0
    alignment = False
    
    parser = argparse.ArgumentParser(description="Your script description here")

    # Add command-line argument for JSON input (file or string)
    parser.add_argument("--parameters", "-c", required=True, help="Number of rings")
    parser.add_argument("--segments", "-s", required=True, help="Number of rings")
    parser.add_argument("--bridges", "-b", required=True, help="Number of rings")
    parser.add_argument("--arms", "-a", required=True, help="Number of rings")
    parser.add_argument("--ports", "-p", required=True, help="Number of rings")
    parser.add_argument("--viapadstack", "-t", required=True, help="Number of rings")
    parser.add_argument("--via", "-v", required=True, help="Number of rings")
    parser.add_argument("--guardring", "-g", required=True, help="Number of rings")
    parser.add_argument("--layer", "-l", required=True, help="Number of rings")

    parser.add_argument("--output", "-o", help="Output path")
    parser.add_argument("--name", "-n", help="Output file name")


  
    args = parser.parse_args()


    parameter_file_path = args.parameters
    segments_file_path = args.segments
    bridges_file_path = args.bridges
    arms_file_path = args.arms
    ports_file_path = args.ports
    viapadstack_file_path = args.viapadstack
    via_file_path = args.via
    guardring_file_path = args.guardring
    layer_file_path = args.layer

    
    f = open(parameter_file_path, "r")
    parameter_json = json.load(f)

    f = open(segments_file_path, "r")
    segment_json = json.load(f)

    f = open(bridges_file_path, "r")
    bridges_json = json.load(f)

    f = open(arms_file_path, "r")
    arms_json = json.load(f)

    f = open(ports_file_path, "r")
    ports_json = json.load(f)

    f = open(viapadstack_file_path, "r")
    viapadstack_json = json.load(f)

    f = open(via_file_path, "r")
    via_json = json.load(f)

    f = open(guardring_file_path, "r")
    guardring_json = json.load(f)

    f = open(layer_file_path, "r")
    layer_json = json.load(f)


    artwork_description = {}
    artwork_description["parameters"] = parameter_json
    artwork_description["segments"] = segment_json
    artwork_description["arms"] = arms_json
    artwork_description["ports"] = ports_json
    artwork_description["bridges"] = bridges_json
    artwork_description["viaPadStack"] = viapadstack_json
    artwork_description["via"] = via_json
    artwork_description["guardRing"] = guardring_json
    artwork_description["layer"] = layer_json

    output_path = "./"
    output_name = "artwork_description_file.json"

    if args.output:
        output_path = args.output


    if args.name:
        output_path = args.name



    file_path = output_path + output_name
    with open(file_path, 'w') as file:
        json.dump(artwork_description, file, indent=4)


    print(artwork_description)
