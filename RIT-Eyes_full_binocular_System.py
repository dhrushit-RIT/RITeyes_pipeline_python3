'''
Suppliment Library for constructing full binocular system for RIT-Eyes

@author: Chengyi Ma
'''
import os
import sys
#sys.path.append("C:\\Users\\mcy13\\anaconda3\\envs\\RITEyes\\Lib")
#os.environ['PYTHONPATH'] = "C:\Python39"
print("PYTHONPATH: ", os.environ['PYTHONPATH'])
import bpy
import argparse
import pandas as pd
import numpy as np

####	Initialize section starts 	####
## Decide on what to import on start up.
## First, need to understand how the environment works.

## Handle arguments:
argv = sys.argv
if '--' in sys.argv:
    argv = sys.argv[sys.argv.index('--') + 1:]
parser = argparse.ArgumentParser()
parser.add_argument("--model_id", type= int, help='Choose a head model (1-24)', default=1)
parser.add_argument("--person_idx", type=int, help='Person index in the GIW Data folder', default=0)
parser.add_argument('--trial_idx', type=int, help='Trial index in the GIW Data folder', default=0)

args = parser.parse_args()

## Global Variables Start
default_data_path = "" 		# Where all person data rest
data_directory = "" 		# Where the data rest for a particualr person_idx and trial_idx
model_id = args.model_id
person_idx = args.person_idx
trial_idx = args.trial_idx

gaze_data:pd.DataFrame = None
eye_locations = [] # a list of two sub_lists [[eye0x, eye0y, eye0z], [eye1x, eye1y, eye1z]]

## Global Varaiables End

## Initialize Functions Start
def getDataPath():
	"""
	Initialize raw data path from file "data_path.txt"

	Path save to default_data_path
	"""
	try:
		with open('data_path.txt', 'r') as default_data_path_file:
			global default_data_path 
			default_data_path = default_data_path_file.read()
	except Exception:
		print('No data_path.txt file!')
		default_data_path = 'D:/Raw Eye Data/'

def readGazeData(data_directory:str) -> None:
	global gaze_data
	gaze_data = pd.read_csv(os.path.join(data_directory, "exports/gaze_positions.csv"))
	#print(type(gaze_data))
	return None

def getHighestConfidenceFrame(gaze_data_dictList:dict) -> dict:
	'''
	Find the tuples with highest confidence estimation for L and R eyes
	return in a dictionary of 4 pairs of keys and values:
		"L_index" : 		(int)highest_confidence_index_L,
		"L_confidence" : 	(int)highest_confidence_L,
		"R_index" : 		(int)highest_confidence_index_R,
		"R_confidence" : 	(int)highest_confidence_R

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


def getEyelocations(gaze_data:pd.DataFrame):
	'''
	From gaze data, we find the best fit eye locations for both eyes in world camera space.
	'''
	gaze_data_dictList = gaze_data.to_dict("records")
	
	# Find highest confident frame:
	highConfidenceFrameDict = getHighestConfidenceFrame(gaze_data_dictList)
	eye0_highconfidence_tuple_index = highConfidenceFrameDict["L_index"]
	eye1_highconfidence_tuple_index = highConfidenceFrameDict["R_index"]
	
	eye0_location = [
		gaze_data_dictList[eye0_highconfidence_tuple_index]["eye_center0_3d_x"],
		gaze_data_dictList[eye0_highconfidence_tuple_index]["eye_center0_3d_y"],
		gaze_data_dictList[eye0_highconfidence_tuple_index]["eye_center0_3d_z"],
	]

	eye1_location = [
		gaze_data_dictList[eye1_highconfidence_tuple_index]["eye_center1_3d_x"],
		gaze_data_dictList[eye1_highconfidence_tuple_index]["eye_center1_3d_y"],
		gaze_data_dictList[eye1_highconfidence_tuple_index]["eye_center1_3d_z"],
	]

	# for debug
	# print(eye0_highconfidence_tuple_index, eye0_location, eye1_highconfidence_tuple_index, eye1_location)
	return [eye0_location, eye1_location]

def printArgs() -> None:
	'''	For debug, print input arguments '''
	print(args)

## Initialize Functions Ends
getDataPath()
data_directory = os.path.join(default_data_path, str(person_idx), str(trial_idx))
readGazeData(data_directory)
eye_locations = getEyelocations(gaze_data)

####	Initialize section ends 	####
## Blender Scene Edit Starts

print(bpy.app.version_string)

## Blender Scene Edit Ends
