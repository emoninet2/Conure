import math
import json
import copy
import os.path
import sys
import argparse 



def generate_segment(rings, metal, arm, bridge0, bridge1):
    # Base data structure
    n = int(rings)
    data =  {}

    

    metal0 = metal
    arm0 = arm
    bridge0 = bridge0
    bridge1 = bridge1



    # Dynamically determine the number of segments based on n
    num_segments = 8
    seg0group = [None] * n
    seg4group = [None] * n
    for seg in range(8):
        for _ in range(n): 
            if(seg == 0):
                if(_ == n-1):
                    #print("DAMN",seg,  _ ,  "P")
                    seg0group[_] = "P"
    
                else:
                    if(n%2):
                        #print("DAMN",seg,  _ ,  math.pow(-1,_))
                        seg0group[_] = math.pow(-1,_)
       
                    else:
                        #print("DAMN",seg,  _ ,  -math.pow(-1,_) + (_ == 0))
                        seg0group[_] =  -math.pow(-1,_) + (_ == 0)
         

            if(seg == 4):
                if(n%2):
                    #print("DAMN",seg,  _ ,  -math.pow(-1,_) + (_ == 0) )
                    seg4group[_] = -math.pow(-1,_) + (_ == 0)
                else:
                    #print("DAMN",seg,  _ ,  math.pow(-1,_) )
                    seg4group[_] = math.pow(-1,_)

    #print(seg4group, seg0group)


    for seg in range(8):
        group = []
        if seg == 0 or seg == 4:
            for _ in range(n):


                if( seg == 0 and seg0group[_] == "P" ):
                    group.append({
                    "type": "PORT",
                    "data": {
                        "layer": metal0,
                        "arm": arm0
                    }
                    })
                elif(seg == 0 and seg0group[_] == 0):
                    group.append({
                    "type": "DEFAULT",
                    "data": {
                        "layer": metal0,
                    }
                    })
                elif(seg == 4 and seg4group[_] == 0):
                    group.append({
                    "type": "DEFAULT",
                    "data": {
                        "layer": metal0,
                    }
                    })
                elif(seg == 0 and seg0group[_] == -1):
                    group.append({
                    "type": "BRIDGE",
                    "data": {
                        "layer": metal0,
                        "jump": -1,
                        "bridge": bridge1
                    }
                    })
                elif(seg == 0 and seg0group[_] == 1):
                    group.append({
                    "type": "BRIDGE",
                    "data": {
                        "layer": metal0,
                        "jump": 1,
                        "bridge": bridge0
                    }
                    })
                elif(seg == 4 and seg4group[_] == -1):
                    group.append({
                    "type": "BRIDGE",
                    "data": {
                        "layer": metal0,
                        "jump": -1,
                        "bridge": bridge1
                    }
                    })
                elif(seg == 4 and seg4group[_] == 1):
                    group.append({
                    "type": "BRIDGE",
                    "data": {
                        "layer": metal0,
                        "jump": 1,
                        "bridge": bridge0
                    }
                    })
            data[f"S{seg}"] = {"id": seg, "group": group}            

        else:
            group.extend([{
                "type": "DEFAULT",
                "data": {
                    "layer": metal0
                }
            } for _ in range(n - len(group))])

            data[f"S{seg}"] = {"id": seg, "group": group}

    return data



def segment_generator_coplanar_inductor(n, alignment = False, output_path = "./", output_name = "segment.json"):

    segment = {}
    segment["config"] = {}
    segment["config"]["bridge_extension_aligned"] = alignment
    segment["data"]= generate_segment(n, "M9", "A0","B0", "B1")

    #print(segment)

    file_path = output_path + output_name
    with open(file_path, 'w') as file:
        json.dump(segment, file, indent=4)



if __name__ == "__main__":
    rings = 0
    alignment = False
    
    parser = argparse.ArgumentParser(description="Your script description here")

    # Add command-line argument for JSON input (file or string)
    parser.add_argument("--rings", "-r", required=True, help="Number of rings")
    parser.add_argument("--align", "-a", action="store_true", help="Align under cross extensions")
    parser.add_argument("--output", "-o", help="Output path")
    parser.add_argument("--name", "-n", help="Output file name")

    args = parser.parse_args()


    if args.align:
        alignment = True


    segment_generator_coplanar_inductor(args.rings , alignment)