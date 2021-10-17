'''
Script for constructing full binocular system for RIT-Eyes

@author: Chengyi Ma
'''
import os
import sys
#sys.path.append("C:\\Users\\mcy13\\anaconda3\\envs\\RITEyes\\Lib")
#os.environ['PYTHONPATH'] = "C:\Python39"
import argparse
import pandas as pd
import numpy as np
import subprocess
import math
import msgpack
import json
import cv2

####    Initialize section starts   ####
## Decide on what to import on start up.
## First, need to understand how the environment works.

## Handle arguments:

# for debug
print("sys.argv before", sys.argv)

if '--' in sys.argv:
    argv = sys.argv[sys.argv.index('--') + 1:]

parser = argparse.ArgumentParser()
parser.add_argument("--model_id", type= int, help='Choose a head model (1-24)', default=1)
parser.add_argument("--person_idx", type=int, help='Person index in the GIW Data folder', default=0)
parser.add_argument('--trial_idx', type=int, help='Trial index in the GIW Data folder', default=0)
parser.add_argument('--iris_idx', type=int, help='Which iris texture to use(1-9)', default=1)
parser.add_argument('--start_frame', type=int, help='The starting frame to render, >=1', default=0)
parser.add_argument('--end_frame', type=int, help='the ending frame to render, >=2', default=0)
parser.add_argument('--mode', type=str, help='Choose a render mode', default='binocular')

if '--' in sys.argv:
    args = parser.parse_args(argv)
else:
    args = parser.parse_args()

## Constants:
PUPILLARY_DISTANCE = 6

## Global Variables Starts  ##
default_data_path = ""      # Where all person data rest
blender_path = ""
data_directory = ""         # Where the data rest for a particualr person_idx and trial_idx
model_id = args.model_id
person_idx = args.person_idx
trial_idx = args.trial_idx
iris_idx = args.iris_idx

gaze_data:pd.DataFrame = None
gaze_data_dictList = None

pupil_data:pd.DataFrame = None
pupil_data_dict = {}

frame_cap = 0 # the last world video frame index
total_frames = 0 # the total world video's frame number
start_frame = args.start_frame
end_frame = args.end_frame

render_mode = args.mode

Head_info = None

# In Blender Gloabl Variables
camera0 = None
camera1 = None
ob_camera = None
Eye0 = None
Eye1 = None
Armature = None
head = None
video_plane = None
gaze_object = None

# Render Variables
device_type = 'OPTIX'
output_folder = "renderings"
binocular_output_folder = "binocular"


## Global Varaiables Ends   ##

#### Blender Initialization Starts ####
isBlenderProcess = False
#blender_path = "/media/renderings/T7/RITEyes/blender-2.93.4-linux-x64/blender"
#blender_path = "D:/Softwares/Blender/blender.exe"
#blender_path = "/media/renderings/New Volume/RITEyes/blender-2.93.3-linux-x64/blender"

## Try to read
try:
    with open('blender_path.txt', 'r') as default_blender_path_file:
        blender_path = default_blender_path_file.read().strip()
except Exception:
    print('No blender_path.txt file!')
    blender_path = "/media/renderings/T7/RITEyes/blender-2.93.4-linux-x64/blender"

try:
    import bpy
    print("which bpy? ", bpy.__file__)
    isBlenderProcess = True
except ModuleNotFoundError:
    print("Blender not detected, starting Blender now")
    subprocess.call([
        blender_path, 
        '-b',
        '--python','RIT-Eyes_full_binocular_System.py',
        '--',
        '--model_id',
        str(args.model_id),
        '--person_idx',
        str(args.person_idx),
        '--trial_idx',
        str(args.trial_idx),
        '--start_frame',
        str(args.start_frame),
        '--end_frame',
        str(args.end_frame),
        '--mode',
        str(args.mode),
        ])
    sys.exit()

print("isBlenderProcess", isBlenderProcess)


#### Blender Initialization Ends ####

## Initialize Functions Start
def getDataPath():
    """
    Initialize raw data path from file "data_path.txt"

    Path save to default_data_path
    """
    try:
        with open('data_path.txt', 'r') as default_data_path_file:
            global default_data_path 
            default_data_path = default_data_path_file.read().strip()
    except Exception:
        print('No data_path.txt file!')
        default_data_path = 'D:/Raw Eye Data/'

def readGazeData(data_directory:str) -> None:
    global gaze_data
    gaze_data = pd.read_csv(os.path.join(data_directory, "exports/gaze_positions.csv"))
    global gaze_data_dictList
    gaze_data_dictList = gaze_data.to_dict("records")
    #print(type(gaze_data))
    return None

def readPupilData(data_directory:str) -> None:
    '''
    Read pupil_position.csv file and convert to a dictionary for efficiency
    '''
    print("Processing pupil data...")
    global pupil_data, pupil_data_dict
    pupil_data = pd.read_csv(os.path.join(data_directory, "exports/pupil_positions.csv"))
    pupil_data_dictList = pupil_data.to_dict("records")

    for l in pupil_data_dictList:
        if l["method"] != '2d c++':
            pupil_data_dict[l["pupil_timestamp"]] = l

    

def getHighestConfidenceFrame(gaze_data_dictList:dict) -> dict:
    '''
    Find the tuples with highest confidence estimation for L and R eyes
    return in a dictionary of 4 pairs of keys and values:
        "L_index" :         (int)highest_confidence_index_L,
        "L_confidence" :    (int)highest_confidence_L,
        "R_index" :         (int)highest_confidence_index_R,
        "R_confidence" :    (int)highest_confidence_R

    '''
    highest_confidence_L = 0.0
    highest_confidence_index_L = 0
    highest_confidence_R = 0.0
    highest_confidence_index_R = 0

    for i in range(0, len(gaze_data_dictList)):
        float(gaze_data_dictList[i]["confidence"])
        this_confidence = float(gaze_data_dictList[i]["confidence"])

        if this_confidence >= highest_confidence_L:
            if pd.isna(gaze_data_dictList[i]["eye_center0_3d_x"]):
                pass
            else:
                highest_confidence_L = this_confidence
                highest_confidence_index_L = i

        if this_confidence >= highest_confidence_R:
            if pd.isna(gaze_data_dictList[i]["eye_center1_3d_x"]):
                pass
            else:
                highest_confidence_R = this_confidence
                highest_confidence_index_R = i

        if highest_confidence_L == 1.0 and highest_confidence_R == 1.0:
            break

    return {
        "L_index" : highest_confidence_index_L,
        "L_confidence" : highest_confidence_L,
        "R_index" : highest_confidence_index_R,
        "R_confidence" : highest_confidence_R
    }


def printArgs() -> None:
    ''' For debug, print input arguments '''
    print(args)

def readCalibData() -> list:
    '''
    Read calibration data file for camera matrices
    '''
    calib_directory = os.path.join(default_data_path, str(person_idx), str(trial_idx), "calibrations")
    calib_file_list = os.listdir(calib_directory)
    calib_file_name = calib_file_list[0] # assume that there is only one file
    calib_file_path = os.path.join(calib_directory, calib_file_name)

    with open(calib_file_path, "rb") as calib_file:
        calib_byte_data= calib_file.read()

    calib_data_loaded = msgpack.unpackb(calib_byte_data, use_list=False, strict_map_key=False)
    json_str = json.dumps(calib_data_loaded, indent = 4)
    jsonfile = json.loads(json_str)

    camera0_matrix = jsonfile["data"]["calib_params"]["binocular_model"]["eye_camera_to_world_matrix0"]
    camera1_matrix = jsonfile["data"]["calib_params"]["binocular_model"]["eye_camera_to_world_matrix1"]

    return [camera0_matrix, camera1_matrix]

def readHeadInfo():
    global Head_info
    head_info_path = os.path.join(os.getcwd(), "static_model", "HeadModelInfo.json")
    with open(head_info_path) as json_file:
        json_str = json_file.read()
        Head_info = json.loads(json_str)




## Initialize Functions Ends

getDataPath()
data_directory = os.path.join(default_data_path, str(person_idx), str(trial_idx))
readGazeData(data_directory)
readPupilData(data_directory)
readHeadInfo()


####	Data Processing	Starts	####

##	Data Processing Functions ##
def splitGazeDataByFrame() -> list:
    '''
    Split gaze_data_dictList into smaller lists of dictionaries. Each smaller list has dictionarys with same world_index

    return: list<list<dict>, list<dict>> 
    '''
    frameDictListsByWorldIndex = []
    singleFrameList:list = []

    last_world_frame = 0
    for i in gaze_data_dictList:
        world_frame = int(i["world_index"])
        if last_world_frame == world_frame:
            singleFrameList.append(i)
        elif (world_frame > last_world_frame):

            # if there is a frame drop
            if (world_frame - last_world_frame) > 1:
                frame_difference = world_frame - last_world_frame
                for x in range(1, frame_difference):
                    frameDictListsByWorldIndex.append([])

            frameDictListsByWorldIndex.append(singleFrameList.copy())
            singleFrameList = []
            singleFrameList.append(i)
            last_world_frame = world_frame
        else:
            continue

    if len(singleFrameList) != 0:
        frameDictListsByWorldIndex.append(singleFrameList.copy())

    return frameDictListsByWorldIndex

def _debug_FindMissingFrame(frameDictListsByWorldIndex:list):
    index = 1
    for l in frameDictListsByWorldIndex:
        data_world_index = int(l[0]["world_index"])
        step = data_world_index - index
        if step == 1:
            index = data_world_index
        elif step > 1:
            print("Missing world index:", index+1)
            index = data_world_index

def findBestFrameData(world_frame:int, frameDictListsByWorldIndex:list):
    '''
    Find the best frame data from multiple data tuples in a world frame.
    Consider the highest confidence first. 
    '''
    Eye0_best = None
    Eye1_best = None

    try: 
        data_list = frameDictListsByWorldIndex[world_frame]
    except:
        print("world frame index error:", world_frame)
    #print(data_list, world_frame) # for debug

    # Loop through all data in a world frame
    # Loop for Eye0 First
    best_confidence = 0.0
    data_list_size = len(data_list)

    for e in range(0,data_list_size):
        data_confidence = float(data_list[e]["confidence"])
        # print(world_frame, e," - Data confidence:", data_confidence) # for debug
        if pd.isna(data_list[e]["eye_center0_3d_x"]):
            continue
        else:
            if data_confidence == 1.0:
                Eye0_best = e
                break
            elif data_confidence > best_confidence:
                best_confidence = data_confidence
                Eye0_best = e
    

    # Loop for Eye1 Next
    best_confidence = 0.0
    data_list_size = len(data_list)

    for e in range(0,data_list_size):
        data_confidence = float(data_list[e]["confidence"])
        #print(world_frame, e," - Data confidence:", data_confidence) # for debug
        if pd.isna(data_list[e]["eye_center1_3d_x"]):
            continue
        else:
            if data_confidence == 1.0:
                Eye1_best = e
                break
            elif data_confidence >= best_confidence:
                best_confidence = data_confidence
                Eye1_best = e
    

    return [Eye0_best, Eye1_best]

def _debug_checkmismatch(frameDictListsByWorldIndex):
    index = 0
    for i in frameDictListsByWorldIndex:
        if len(i) == 0:
            index += 1
            continue

        if int(i[0]["world_index"]) != index:
            print("Find index mismatch", index, int(i[0]["world_index"]))
            break
            index += 1

def DetermineFrameRange():
    global end_frame, start_frame
    if end_frame == 0:
        end_frame = frame_cap
    if start_frame == 0:
        start_frame = 1
    #print("Debug:", args.start_frame, args.start_frame)
    print("Rendering frame range from " + str(start_frame) + " to " + str(end_frame))



## Data Processing ##

frameDictListsByWorldIndex = splitGazeDataByFrame()
frame_cap = int(frameDictListsByWorldIndex[-1][-1]["world_index"])
total_frames = len(frameDictListsByWorldIndex)
print("Total world frames in this video: ", total_frames)
print("Framecap: ", frame_cap)
## print(pd.isna(frameDictListsByWorldIndex[0][1]["eye_center1_3d_x"])) # See if a value is missing as nan
#print(findBestFrameData(2, frameDictListsByWorldIndex)) # for debug, testing frameDictListsByWorldIndex

camera_matrices = readCalibData() # get camera pos and rotation information

DetermineFrameRange() # decide what is the range for render


####	Data Processing Ends 	####



####    Initialize section ends     ####

####    Blender Scene Edit Starts   ####

## Blender Opertaion Functions:
def openBlenderFile():
    '''
    Open Blender file from Command Line Argument
    '''
    if args.model_id != 0:
        bpy.ops.wm.open_mainfile(filepath=os.path.join("static_model",str(args.model_id),str(args.model_id)+"_v9-pupil.blend"))

def selectObjectHierarchy(obj):
    '''
    Select the whole hierarchy from a give parent obj, Be aware of that it only looks downward to the children.
    '''
    obj.select_set(True)
    for child_obj in obj.children:
        selectObjectHierarchy(child_obj)

def hideObjectHierarchy(obj):
    '''
    hide an obj and its all children
    '''
    obj.hide_set(True)
    obj.hide_render = True
    for child_obj in obj.children:
        hideObjectHierarchy(child_obj)

def unhideObjectHierarchy(obj):
    obj.hide_set(False)
    obj.hide_render = False
    for child_obj in obj.children:
        unhideObjectHierarchy(child_obj)

def setUpGazeAnimationFrames(frameCount:int, Eye0, Eye1, frameDictListsByWorldIndex):
    '''
    Use processed data to set up Eyes' location and rotation for each frame
    '''
    print("Setting up eye frames from gaze data...")
    # Loop through all frames
    for frame_index in range(0, frameCount):
        Eyes_best_data = findBestFrameData(frame_index, frameDictListsByWorldIndex)

        # Setting up Eye0 frame
        eye0_pupil_timestamp = 0
        if (Eyes_best_data[0] != None):
            Eye0_dataDict = frameDictListsByWorldIndex[frame_index][Eyes_best_data[0]]
            Eye0.location[0] = Eye0_dataDict["eye_center0_3d_x"] * 0.1
            Eye0.location[1] = Eye0_dataDict["eye_center0_3d_y"] * 0.1
            Eye0.location[2] = Eye0_dataDict["eye_center0_3d_z"] * 0.1

            Eye0.rotation_euler[0] = -Eye0_dataDict["gaze_normal0_x"]
            Eye0.rotation_euler[1] = Eye0_dataDict["gaze_normal0_y"] ##
            Eye0.rotation_euler[2] = Eye0_dataDict["gaze_normal0_z"]

            Eye0.keyframe_insert(data_path="location", frame=frame_index)
            eye0_pupil_timestamp = GetPupilTimeStampFromBase(Eye0_dataDict["base_data"], 0)

        Eye0.keyframe_insert(data_path="location", frame=frame_index)
        Eye0.keyframe_insert(data_path="rotation_euler", frame=frame_index)

        # set eye0 pupil size
        #print("Debug: pupil size data:", Eye0_dataDict["base_data"], 0, eye0_pupil_timestamp)
        #[float(((x / 2) * (0.8 / 3)) - (0.5 / 3)) for x in pupil]
        try:
            eye0_pupil_timestamp = GetPupilTimeStampFromBase(Eye0_dataDict["base_data"], 0)
            bpy.data.meshes['Roundcube.000'].shape_keys.key_blocks["Pupil contract"].value = float(((pupil_data_dict[eye0_pupil_timestamp]["diameter_3d"] / 2) * (0.8 / 3)) - (0.5 / 3))
            bpy.data.meshes['Roundcube.000'].shape_keys.key_blocks["Pupil contract"].keyframe_insert(data_path="value",frame=frame_index)
        except:
            print("Error on setting pupil:", "timestamp: ", eye0_pupil_timestamp)

        # Setting up Eye1 frame
        eye1_pupil_timestamp=0
        if (Eyes_best_data[1] != None):
            Eye1_dataDict = frameDictListsByWorldIndex[frame_index][Eyes_best_data[1]]
            Eye1.location[0] = Eye1_dataDict["eye_center1_3d_x"] * 0.1
            Eye1.location[1] = Eye1_dataDict["eye_center1_3d_y"] * 0.1
            Eye1.location[2] = Eye1_dataDict["eye_center1_3d_z"] * 0.1

            Eye1.rotation_euler[0] = -Eye1_dataDict["gaze_normal1_x"]
            Eye1.rotation_euler[1] = Eye1_dataDict["gaze_normal1_y"]
            Eye1.rotation_euler[2] = Eye1_dataDict["gaze_normal1_z"]

            eye1_pupil_timestamp = GetPupilTimeStampFromBase(Eye1_dataDict["base_data"], 1)

            
        Eye1.keyframe_insert(data_path="location", frame=frame_index)
        Eye1.keyframe_insert(data_path="rotation_euler", frame=frame_index)

        # set eye1 pupil size
        try:
            eye1_pupil_timestamp = GetPupilTimeStampFromBase(Eye1_dataDict["base_data"], 1)
            bpy.data.meshes['Roundcube.001'].shape_keys.key_blocks["Pupil contract"].value = float(((pupil_data_dict[eye1_pupil_timestamp]["diameter_3d"] / 2) * (0.8 / 3)) - (0.5 / 3))
            bpy.data.meshes['Roundcube.001'].shape_keys.key_blocks["Pupil contract"].keyframe_insert(data_path="value",frame=frame_index)
        except:
            print("Error on setting pupil:", "timestamp:", eye1_pupil_timestamp)

        # set gaze object animation
        try: 
            if (Eyes_best_data[0] != None):
                Eye0Gaze_dataDict = frameDictListsByWorldIndex[frame_index][Eyes_best_data[0]]
                normX = Eye0Gaze_dataDict["norm_pos_x"]
                normY = Eye0Gaze_dataDict["norm_pos_y"]
            else:
                Eye1Gaze_dataDict = frameDictListsByWorldIndex[frame_index][Eyes_best_data[1]]
                normX = Eye1Gaze_dataDict["norm_pos_x"]
                normY = Eye1Gaze_dataDict["norm_pos_y"]
            SetGazeObject(
                frame_index,
                video_plane,
                gaze_object,
                normX,
                normY
            )
        except:
            print("Error: Failed to set Gaze object, frame_index: ", frame_index)

    print("Completed setting eye frames.")

def GetPupilTimeStampFromBase(data_str:str, eye_index:int):
    '''
    A helper function to split base_data str from gaze data
    base data could be a single timestamp or a double.

    return the timestamp match in pupil data
    '''
    data_str_tokens = data_str.split(" ")
    timestamp = 0
    if len(data_str_tokens) == 1:
        # if this is a single timstamp data
        timestamp = float(data_str_tokens[0].split("-")[0])
    elif len(data_str_tokens) == 2:
        timestamp_list1 = data_str_tokens[0].split("-")
        timestamp_list2 = data_str_tokens[1].split("-")

        if eye_index == 0:
            timestamp = float(timestamp_list1[0])
        else:
            timestamp = float(timestamp_list2[0])

    return timestamp

def add_view_vector():
    '''
    An optional feature, add a blender curve in the position of the eyeball model to observe the gaze direction.
    Do this before copying Eye0
    '''
    bpy.ops.object.select_all(action="DESELECT")
    #bpy.ops.curve.primitive_nurbs_path_add(radius=100, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1), rotation=(0, 0, 0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.1, depth=100, enter_editmode=False, align='WORLD', location=(0, 0, 50), scale=(1, 1, 1))
    # bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    eye_vector = bpy.data.objects['Cylinder']
    eye_vector.name = "Gaze_Indicator"
    eye_vector.parent = Eye0
    # eye_vector.rotation_euler[1] = math.radians(90)
    # eye_vector.location[2] = 100
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN')
    bpy.ops.object.select_all(action="DESELECT")

    eye_vector_mat = bpy.data.materials.new("EyeVectorMat")
    # eye_vector_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0, 0, 1)
    eye_vector_mat.diffuse_color = 1,0,0,1
    eye_vector.data.materials.append(eye_vector_mat)
    eye_vector.active_material_index = len(eye_vector.data.materials) - 1



def getFullRotationVector(rod_vector):
    '''
    Convert a 3-number rotation vector from cv2.rodrigues to a full angle-axis rotation vector.
    '''
    theta = math.sqrt(math.pow(rod_vector[0], 2) + math.pow(rod_vector[1], 2) + math.pow(rod_vector[2], 2))
    unit_vector = [rod_vector[0][0]/theta, rod_vector[1][0]/theta, rod_vector[2][0]/theta]

    return np.asarray([theta, unit_vector[0], unit_vector[1], unit_vector[2]])

def setEyeCameras(camera_matrices):
    '''
    Set eye camera based on camera_matrices:
    '''
    global camera1, camera0
    # set camera 0
    camera0_matrix = camera_matrices[0]
    camera0_matrix = np.asarray(camera0_matrix)
    camera0_rotation_matrix = camera0_matrix[:3, :3]
    camera0_rotation_vector = cv2.Rodrigues(camera0_rotation_matrix)[0]
    camera0_fullRotVector = getFullRotationVector(camera0_rotation_vector)
    print("Camera0 full rotation vector: ", camera0_fullRotVector)

    # Test using rotation matrix instead
    camera0_rotation = np.array([0, 1, 0])
    camera0_rotation = np.matmul(camera0_rotation_matrix, camera0_rotation)
    print("Camera 0 rotation: ", camera0_rotation)

    #print("Eye camera0 rotation vector: ", camera0_rotation_vector)
    camera0_translation_vector = camera0_matrix[:3, 3]
    print("Eye camera0 translation vector:", camera0_translation_vector)
    # Add camera with data
    bpy.ops.object.camera_add(
        enter_editmode=False, 
        align='VIEW', 
        location=(camera0_translation_vector[0] * 0.1, camera0_translation_vector[1] * 0.1, camera0_translation_vector[2] * 0.1), 
        rotation=(0, 0, 0), 
        scale=(0.01, 0.01, 0.01)
        )
    camera0 = bpy.data.objects["Camera"]
    camera0.name = "Camera0"
    camera0.scale[0] = 0.01
    camera0.scale[1] = 0.01
    camera0.scale[2] = 0.01

    # Set camera rotation
    camera0.rotation_mode = 'AXIS_ANGLE'
    camera0.rotation_axis_angle = camera0_fullRotVector

    # changes the FOV
    camera0.data.lens_unit = 'FOV'
    camera0.data.angle = math.radians(51)

    # Camera orientation fix 180 (to compensate Blender has camera forward vector pointing to -z by default)
    camera0.rotation_mode = 'XYZ'
    camera0.rotation_euler[0] += 3.14159



    # set camera 1
    camera1_matrix = camera_matrices[1]
    camera1_matrix = np.asarray(camera1_matrix)
    camera1_rotation_matrix = camera1_matrix[:3, :3]
    camera1_rotation_vector = cv2.Rodrigues(camera1_rotation_matrix)[0]
    camera1_fullRotVector = getFullRotationVector(camera1_rotation_vector)
    print("Camera1 full rotation vector: ", camera1_fullRotVector)

    camera1_translation_vector = camera1_matrix[:3, 3]
    print("Eye camera1 translation vector:", camera1_translation_vector)
    # Add camera with data
    bpy.ops.object.camera_add(
        enter_editmode=False, 
        align='VIEW', 
        location=(camera1_translation_vector[0] * 0.1, camera1_translation_vector[1] * 0.1, camera1_translation_vector[2] * 0.1), 
        rotation=(camera1_rotation_vector[0], camera1_rotation_vector[1], camera1_rotation_vector[2]), 
        scale=(0.01, 0.01, 0.01)
        )
    camera1 = bpy.data.objects["Camera"]
    camera1.name = "Camera1"
    camera1.scale[0] = 0.01
    camera1.scale[1] = 0.01
    camera1.scale[2] = 0.01

    # set camera rotation
    camera1.rotation_mode = 'AXIS_ANGLE'
    camera1.rotation_axis_angle = camera1_fullRotVector

    # changes the FOV
    camera1.data.lens_unit = 'FOV'
    camera1.data.angle = math.radians(51)
    
    # Camera orientation fix 180 (to compensate Blender has camera forward vector pointing to -z by default)
    camera1.rotation_mode = 'XYZ'
    camera1.rotation_euler[0] += 3.14159

def EyeCameraSettings(camera0, camera1):
    '''
    Set up camera parameters to get correct render result.
    '''
    camera0.data.lens = 5.1
    camera0.data.sensor_width = 7.06

    camera1.data.lens = 5.1
    camera1.data.sensor_width = 7.06

def RenderSetting():
    import bpy
    import cycles
    RenderDeviceSetting()

    # Scene Output settings
    s = bpy.context.scene
    # Image resolution
    s.render.resolution_x = 640
    s.render.resolution_y = 480
    s.render.tile_x = 640
    s.render.tile_y = 480
    s.cycles.device = 'GPU'
    s.render.image_settings.file_format = 'TIFF'

def RenderDeviceSetting():
    preferences = bpy.context.preferences
    cycles_preferences = preferences.addons["cycles"].preferences
    bpy.context.scene.cycles.device = 'GPU'

    # Use all available devices
    print("USING THE FOLLOWING GPUS:")
    cuda_devices, opencl_devices = cycles_preferences.get_devices()
    print("Available devices", cycles_preferences.get_devices()) # for debug
    devices=[]
    for x in range(len(cycles_preferences.devices)):
        if cycles_preferences.devices[x] in cuda_devices:
            devices.append(cycles_preferences.devices[x])
    for x in range(len(devices)):
        print(devices[x].name)
        devices[0].use = True

    print("Computer device type =" , cycles_preferences.compute_device_type) # for debug
    cycles_preferences.compute_device_type = device_type

def LoadEyeTextures():
    # Loading all textures
    # Loading all textures
    # Iris texture
    iris_mat = bpy.data.materials['Iris.000']
    # Sclera texture
    sclera_mat = bpy.data.materials['Sclera material.000']
    skin = bpy.data.materials['skin']


    iris_mat = bpy.data.materials['Iris.000']
    sclera_mat = bpy.data.materials['Sclera material.000']
    ir  =os.path.join(os.getcwd(),'Textures_eye','ir-textures/')
    scl =os.path.join(os.getcwd(),'Textures_eye','sclera/')
    env_path = os.path.join(os.getcwd(),'environmental_textures/')

    sclera_mat.node_tree.nodes["op"].image = bpy.data.images.load(filepath=os.path.join(os.getcwd(),'Textures_eye','opacity.png'))
    sclera_mat.node_tree.nodes["sclera"].image = bpy.data.images.load(filepath=os.path.join(os.getcwd(),'Textures_eye','Sclera color.png'))
    sclera_mat.node_tree.nodes["Imagen.003"].image = bpy.data.images.load(filepath=os.path.join(os.getcwd(),'Textures_eye','sclera_bump.png'))

    iris_mat.node_tree.nodes["iris"].image = bpy.data.images.load(filepath=os.path.join(ir, str(iris_idx)+'.png'))

def RenderImageSequence():
    '''
    Renders the image settings with Binocular render settings
    '''
    s = bpy.context.scene


    for i in range(start_frame, end_frame):
        try:
            s.node_tree.links.new(s.node_tree.nodes["Render Layers"].outputs['Image'],
                                  s.node_tree.nodes["Composite"].inputs[0])
        except:
            print('No node')

        frame = i
        
        IndividualEyeRender(0, frame)
        IndividualEyeRender(1, frame)

def IndividualEyeRender(EyeCameraIndex, frame_index):
    '''
    A helper method to render with particular eye camera
    '''
    s = bpy.context.scene

    EyeCameraName = ""
    if EyeCameraIndex == 0:
        EyeCameraName = "Eye0"
    else:
        EyeCameraName = "Eye1"

    s.frame_current = frame_index
    filename = os.path.join(os.getcwd(), output_folder, binocular_output_folder, str(person_idx), str(trial_idx), EyeCameraName,
                                str(s.frame_current).zfill(4) + ".tif")
    if os.path.isfile(os.path.join(output_folder, binocular_output_folder, str(person_idx), str(trial_idx), EyeCameraName,
                                       str(s.frame_current).zfill(4) + ".tif")):
        print("skipped ", filename)
    else:
        print(frame_index)
        s.render.filepath = filename

        if EyeCameraIndex == 0:
            s.camera = camera0
        else:
            s.camera = camera1

        bpy.ops.render.render(  # {'dict': "override"},
            # 'INVOKE_DEFAULT',
            False,  # undo support
            animation=False,
            write_still=True)

def ObserveRender():
    '''
    Render with an additional observe camera
    '''

    add_view_vector() # 

    ObserveCameraSetting()
    ob_camera.location = [0, -10, -60]
    ob_camera.rotation_euler = [3.05, 0, 0]

    RenderDeviceSetting()

    s = bpy.context.scene
    s.camera = ob_camera
    s.render.resolution_x = 1920
    s.render.resolution_y = 1080

    s.render.tile_x = 640
    s.render.tile_y = 480
    s.cycles.device = 'GPU'
    s.render.image_settings.file_format = 'TIFF'

    for i in range(start_frame, end_frame):
        try:
            s.node_tree.links.new(s.node_tree.nodes["Render Layers"].outputs['Image'],
                                  s.node_tree.nodes["Composite"].inputs[0])
        except:
            print('No node')

        frame = i
        s.frame_current = frame
        filename = os.path.join(os.getcwd(), output_folder, binocular_output_folder, str(person_idx), str(trial_idx), "Observation",
                                str(s.frame_current).zfill(4) + ".tif")
        if os.path.isfile(filename):
            print("skipped ", filename)
        else:
            print(frame)
            s.render.filepath = filename

            bpy.ops.render.render(  # {'dict': "override"},
                # 'INVOKE_DEFAULT',
                False,  # undo support
                animation=False,
                write_still=True)

def RenderPlanner():
    '''
    The master render function, decide what render mode to use and what routine to adopt
    '''
    global render_mode
    if render_mode == "binocular":
        RenderSetting()
        RenderImageSequence()
    elif render_mode == "observe":
        ObserveRender()

def ObserveCameraSetting():
    '''
    Add an extra observe camera for rendering
    '''
    global ob_camera
    bpy.ops.object.camera_add(
        enter_editmode=False, 
        align='VIEW', 
        location=(0, 0, 0), 
        rotation=(3.14159, 0, 0), 
        scale=(0.01, 0.01, 0.01)
        )
    ob_camera = bpy.data.objects["Camera"]
    ob_camera.name = "ObCamera"

def setHeadModel():
    '''
    Set the head position to a calculated position based on pupillary distance
    '''
    global Armature
    unhideObjectHierarchy(Armature)

    Armature.location = [-4, 1.5, -2]
    Armature.rotation_euler = [-1.5708, 0, 3.14159]

    model_scale = PUPILLARY_DISTANCE / Head_info[str(model_id)]["pupillary distance"]
    Armature.scale = [model_scale, model_scale, model_scale]
    setHeadModelMaterial()

def setHeadModelMaterial():
    '''
    Fix head model material problem
    '''
    skin = bpy.data.materials['skin']
    skin.node_tree.nodes["c1"].image =bpy.data.images.load(filepath= os.path.join(os.getcwd(),'static_model',str(model_id),'Textures','c.jpg'))
    skin.node_tree.nodes["c2"].image = bpy.data.images.load(filepath=os.path.join(os.getcwd(),'static_model',str(model_id),'Textures','c1.jpg'))
    skin.node_tree.nodes["g1"].image =bpy.data.images.load(filepath=os.path.join(os.getcwd(),'static_model',str(model_id),'Textures','g.jpg'))
    skin.node_tree.nodes["s1"].image =bpy.data.images.load(filepath=os.path.join(os.getcwd(),'static_model',str(model_id),'Textures','s.jpg'))
    skin.node_tree.nodes["n"].image =bpy.data.images.load(filepath=os.path.join(os.getcwd(),'static_model',str(model_id),'Textures','n.jpg'))

def HeadModifierSettings():
    global head
    head = bpy.data.objects["head"]
    
    eye_warp2 = head.modifiers.new("EyeWarp2", type='WARP')
    eye_warp2.object_from = bpy.data.objects["pupil-empty.001"]
    eye_warp2.object_to = bpy.data.objects["cornea-empty.001"]
    eye_warp2.strength = 0.4
    eye_warp2.falloff_type = 'CURVE'
    eye_warp2.falloff_radius = 0.009

def SetVideoPlane():
    # Creating the plane
    dist = 40
    angle_deg = 88
    half_width = math.tan(math.radians(angle_deg/2))*dist/10

    bpy.ops.mesh.primitive_plane_add(size=20, enter_editmode=False, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    video_plane = bpy.data.objects["Plane"]
    video_plane.scale[0] = half_width
    video_plane.scale[1] = half_width / 16 * 9
    video_plane.location[2] = dist # testing value
    video_plane.rotation_euler[2] = 3.14159

    # set up video material
    bpy.ops.material.new() # create new material
    video_material = bpy.data.materials['Material']
    video_material.name = "Video Material"
    default_BSDF = video_material.node_tree.nodes['Principled BSDF']
    # apply material to plane
    video_plane.active_material = video_material
    # remove default_BSDF
    video_material.node_tree.nodes.remove(default_BSDF)
    # add image texture node
    image_node = video_material.node_tree.nodes.new('ShaderNodeTexImage')
    world_video_path = os.path.join(data_directory, 'world.mp4')
    print("Setting World Video Path for reference image plane:", world_video_path)
    world_video = bpy.data.images.load(world_video_path)
    image_node.image = world_video
    # add seperate and combine rgb node to make video black and white
    separate_rgb_node = video_material.node_tree.nodes.new('ShaderNodeSeparateRGB')
    combine_rgb_node = video_material.node_tree.nodes.new('ShaderNodeCombineRGB')


    # Link nodes
    materialOut_node = video_material.node_tree.nodes['Material Output']
    # video_material.node_tree.links.new( materialOut_node.inputs['Surface'], image_node.outputs['Color'])
    video_material.node_tree.links.new( separate_rgb_node.inputs['Image'], image_node.outputs['Color'])
    video_material.node_tree.links.new( combine_rgb_node.inputs['R'], separate_rgb_node.outputs['R'])
    video_material.node_tree.links.new( combine_rgb_node.inputs['G'], separate_rgb_node.outputs['R'])
    video_material.node_tree.links.new( combine_rgb_node.inputs['B'], separate_rgb_node.outputs['R'])
    video_material.node_tree.links.new( materialOut_node.inputs['Surface'], combine_rgb_node.outputs['Image'])
    # Set video node variables:
    image_node.image_user.frame_duration = frame_cap
    image_node.image_user.use_auto_refresh = True

    return video_plane

def SpawnGazeObject():
    '''
    Add a blue sphere object to indicate the position the eyes are gazing on the video plane.
    '''
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, enter_editmode=False, align='WORLD', location=(0, 0, -10), scale=(1, 1, 1))
    gaze_object = bpy.data.objects['Sphere']
    gaze_object.name = "Gaze_object"

    gaze_object_mat = bpy.data.materials.new("GazeObjectMat")
    gaze_object_mat.diffuse_color = 0,0,1,1
    gaze_object.data.materials.append(gaze_object_mat)
    gaze_object.active_material_index = len(gaze_object.data.materials) - 1

    return gaze_object


def SetGazeObject(frame_index:int, video_plane, gaze_object, norm_X:float, norm_Y:float):
    '''
    using norm_pos from gaze data to set a gaze indicator with an object

    TBD
    '''
    center_x = video_plane.location[0] # video plane locations
    center_y = video_plane.location[1]
    center_z = video_plane.location[2]
    dimension_x = video_plane.dimensions[0] # video plane dimensions
    dimension_y = video_plane.dimensions[1]

    origin_x = center_x + (dimension_x * 0.5)
    origin_y = center_y + (dimension_y * 0.5)

    gaze_posX = origin_x - norm_X * dimension_x
    gaze_posY = origin_y - norm_Y * dimension_y
    gaze_posZ = center_z

    gaze_object.location[0] = gaze_posX
    gaze_object.location[1] = gaze_posY
    gaze_object.location[2] = gaze_posZ

    gaze_object.keyframe_insert(data_path="location", frame=frame_index)
    


## Blender Opertaion Functions Ends ##

## Start Blender
openBlenderFile()

## Blender Objects
Eye0 = bpy.data.objects["Eye.Wetness"]
Eye1 = None
Armature = bpy.data.objects["Armature"]

## Blender Settings:
bpy.context.scene.unit_settings.scale_length = 0.01
bpy.context.scene.unit_settings.length_unit = 'CENTIMETERS'


## Blender Operations

# (Optional) Add a view vector
if args.mode == "observe":
    add_view_vector()

# Hide Objects:
sphere = bpy.data.objects["sphere"]
sphere.hide_render = True

# Rename Scene Camera
scene_camera = bpy.data.objects["Camera"]
scene_camera.name = "SceneCamera"

# changes the FOV
scene_camera.data.lens_unit = 'FOV'
scene_camera.data.angle = math.radians(88)

# Add Eye Cameras
setEyeCameras(camera_matrices)
#EyeCameraSettings(camera0, camera1)

# Copy Eye0 to get a Eye1
bpy.ops.object.select_all(action="DESELECT")
selectObjectHierarchy(Eye0)
bpy.ops.object.duplicate()
bpy.ops.object.select_all(action="DESELECT")
Eye1 = bpy.data.objects["Eye.Wetness.001"]

# Head Model Setting
if render_mode == "observe":
    hideObjectHierarchy(Armature)
elif render_mode == "binocular":
    setHeadModel()

# Add a reference video plane
video_plane = SetVideoPlane()

# Add Gaze Object to the scene
gaze_object = SpawnGazeObject()

# Position two Eyes, Revising, To be finished
setUpGazeAnimationFrames(total_frames - 1, Eye0, Eye1, frameDictListsByWorldIndex)

# set up the ambient light (75%)
bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.5, 0.5, 1)

## Material Setting Start 	##
LoadEyeTextures()

## Material Setting Ends	##

## Modifier Settings:
HeadModifierSettings()

# temporarily save to a file
bpy.ops.wm.save_as_mainfile(filepath="./Stage.blend")

## Rendering Start 	##
RenderPlanner()

# save again after rendering setup
bpy.ops.wm.save_as_mainfile(filepath="./Stage.blend")

## Rendering Ends 	##


#### Blender Scene Edit Ends        ####
