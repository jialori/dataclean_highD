import os
import sys
import pickle
import pandas as pd
import re
from data_management.read_csv import *
from visualization.visualize_frame import VisualizationPlot


# created_arguments = create_args()
created_arguments = {
    "input_path" : "../data/02_tracks.csv",
    "input_static_path" : "../data/01_tracksMeta.csv",
    "input_meta_path" : "../data/01_recordingMeta.csv",
    "pickle_path" : "../data/01.pickle",
    "visualize" : False,
    "background_image" : "../data/01_highway.jpg",
    "plotBoundingBoxes" : True,
    "plotDirectionTriangle" : True,
    "plotTextAnnotation" : True,
    "plotTrackingLines" : True,
    "plotClass" : True,
    "plotVelocity" : True,
    "plotIDs" : True,
    "save_as_pickle" : True,
}

def proc_highd(args):
    f = re.findall(r'[^\\/:*?"<>|\r\n]+$', args["input_path"])[-1]
    out_f = "highD_" + f

    print("Try to find the saved pickle file for better performance.")
    # Read the track csv and convert to useful format
    if os.path.exists(created_arguments["pickle_path"]):
        with open(created_arguments["pickle_path"], "rb") as fp:
            tracks = pickle.load(fp)
        print("Found pickle file {}.".format(created_arguments["pickle_path"]))
    else:
        print("Pickle file not found, csv will be imported now.")
        tracks = read_track_csv(created_arguments)
        print("Finished importing the pickle file.")

    if created_arguments["save_as_pickle"] and not os.path.exists(created_arguments["pickle_path"]):
        print("Save tracks to pickle file.")
        with open(created_arguments["pickle_path"], "wb") as fp:
            pickle.dump(tracks, fp)

    # # Read the static info
    # try:
    #     static_info = read_static_info(created_arguments)
    # except:
    #     print("The static info file is either missing or contains incorrect characters.")
    #     sys.exit(1)

    # # Read the video meta
    # try:
    #     meta_dictionary = read_meta_info(created_arguments)
    # except:
    #     print("The video meta file is either missing or contains incorrect characters.")
    #     sys.exit(1)

    # if created_arguments["visualize"]:
    #     if tracks is None:
    #         print("Please specify the path to the tracks csv/pickle file.")
    #         sys.exit(1)
    #     if static_info is None:
    #         print("Please specify the path to the static tracks csv file.")
    #         sys.exit(1)
    #     if meta_dictionary is None:
    #         print("Please specify the path to the video meta csv file.")
    #         sys.exit(1)
    #     visualization_plot = VisualizationPlot(created_arguments, tracks, static_info, meta_dictionary)
    #     visualization_plot.show()


    tracks_dump = tracks.copy()
    lst_df_tracks = []
    for x in tracks_dump:
        x = x.copy()
        lst_cols = ['frame','bbox','xVelocity','yVelocity','xAcceleration','yAcceleration','frontSightDistance','backSightDistance','thw','ttc','dhw','precedingXVelocity','precedingId','followingId','leftFollowingId','leftAlongsideId','leftPrecedingId','rightFollowingId','rightAlongsideId','rightPrecedingId','laneId']
        df_track = pd.json_normalize(x, max_level=2).explode(column=lst_cols)
        lst_df_tracks.append(df_track)
    df_tracks_full = pd.concat(lst_df_tracks)

    cols = ['id','frame','bbox','xVelocity','yVelocity','xAcceleration','yAcceleration','precedingId','followingId','leftFollowingId','leftAlongsideId','leftPrecedingId','rightFollowingId','rightAlongsideId','rightPrecedingId']

    # 一个frame里最多29辆车。
    # df_tracks.groupby(['frame']).count().avg()

    # END GOAL:
    # result_columns = ['ID', 'frame', 'xmins', 'ymins', 'xmaxs', 'ymaxs', 'xvelocity','yvelocity', 'relations']
    #     relations_columns = ['ID', 'label', 'relative_x', 'relative_y', 'relative_xvelocity', 'relative_yvelocity', 'collide']
    df_tracks = df_tracks_full[cols]
    df_tracks.set_index(['id'], inplace=True, drop=False)
    # df_tracks.set_index(['id', 'frame'], inplace=True)

    df = df_tracks.loc[:,["bbox"]]
    df.loc[:,['xmin', 'ymax', 'width', 'height']] = df["bbox"].to_list()
    df.loc[:,'xmax'] = df.loc[:,"xmin"]+df.loc[:,'width']
    df.loc[:,'ymin'] = df.loc[:,"ymax"]-df.loc[:,'height']
    df.loc[:,'xcenter'] = df.loc[:,"xmin"]+(df.loc[:,'width']/2)
    df.loc[:,'ycenter'] = df.loc[:,"ymax"]-(df.loc[:,'height']/2)
    df_tracks.loc[:,'xmin'] = df.loc[:,'xmin']
    df_tracks.loc[:,'ymin'] = df.loc[:,'ymin']
    df_tracks.loc[:,'xmax'] = df.loc[:,'xmax']
    df_tracks.loc[:,'ymax'] = df.loc[:,'ymax']
    df_tracks.loc[:,'xcenter'] = df.loc[:,'xcenter']
    df_tracks.loc[:,'ycenter'] = df.loc[:,'ycenter']

    df_tracks1 = df_tracks.copy()
    # END GOAL:
    # result_columns = ['ID', 'frame', 'xmins', 'ymins', 'xmaxs', 'ymaxs', 'xvelocity','yvelocity', 'relations']
    #     relations_columns = ['ID', 'label', 'relative_x', 'relative_y', 'relative_xvelocity', 'relative_yvelocity', 'collide']

    df_tracks = df_tracks1.rename(columns={'frame':'id_frame'}, )
    df_tracks = df_tracks.set_index(['id', 'id_frame'], drop=False)
    df_tracks = df_tracks.rename(columns={'id_frame':'frame'}, )

    relations_columns = ['id', 'relative_x', 'relative_y', 'relative_x_velocity', 'relative_y_velocity', 'collide']
    df_tracks.loc[:,"relations"] = None
    df_tracks.loc[:,"collide"] = None
    # print(df_tracks)
    for frame, df_group in df_tracks.groupby('frame'):
        print("calculating...", frame)
        for row_index, row in df_group.iterrows():
            # row_index, id_frame = row_index
            df_group[['relative_x', 'relative_y', 'relative_x_velocity', 'relative_y_velocity']] = df_group.loc[:,['xcenter', 'ycenter','xVelocity', 'yVelocity']]-row[['xcenter', 'ycenter','xVelocity', 'yVelocity']]
            df_group['collide'] = (df_group['xmin']<row['xmax']) & (df_group['xmax']>row['xmin']) & (df_group['ymin']<row['ymax']) & (df_group['ymax']<row['ymin'])
            df_group['collide2'] = (row['xmin']<df_group['xmax']) & (row['xmax']>df_group['xmin']) & (row['ymin']<df_group['ymax']) & (row['ymax']<df_group['ymin'])
            df_group['collide'] = df_group['collide'] | df_group['collide2']
            df_relations = df_group[relations_columns]
            df_relations = df_relations.drop(row_index) # drop itself
            json_relations = df_relations.to_json(orient='records')
            # df_group = df_group.rename(columns={'id':'ID'})
            df_tracks.at[row_index, 'relations'] = json_relations 
            df_tracks.at[row_index, 'collide'] = df_relations['collide'].any() 
            # break
        # break
    # print(df_tracks[df_tracks['frame']==1])

    result_columns = ['id', 'frame', 'collide', 'xmin', 'ymin', 'xmax', 'ymax', 'xVelocity','yVelocity', 'relations']
    print(df_tracks[df_tracks['frame']==1][result_columns])
    df_tracks[result_columns].to_csv(out_f)
if __name__ == "__main__":
    # extract all files under a directory path
    csv_files = []
    print("hey")
    for root, dirs, files in os.walk(r"C:\Users\lorij\Downloads\highd-dataset-v1.0\data"):
        print("hey")
        print(files)
        for file in files:
            if file.endswith("_tracks.csv"):
                print(os.path.join(root, file))
    for csv_file in csv_files:
        created_arguments["input_path"] = csv_file
        proc_highd(created_arguments)
