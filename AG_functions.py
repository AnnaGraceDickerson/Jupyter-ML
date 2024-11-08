import os
import scipy.io
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import load_intan_rhd_format as intan

# displays a dataframe that holds silicone probe recording voltage data
# data: a voltage/electrode-across-time array in dataframe form
def printDF(data):
    print("Electrodes/Rows:", data.shape[0], "\nTime points/Columns:", data.shape[1])
    print("\nTop 5:", data.head())
    print("\nBottom 5:", data.tail())

# downsamples voltage/electrode-across-time by a given factor
# data: a voltage/electrode-across-time array in dataframe form
# alpha: the factor you want to downsample by
def direct_downsample(data, alpha):    
    df = []
    
    for i in range(0, data.shape[1], alpha):
        df.append(data[i])

    return df

# converts sample number associated with voltage data to time in seconds the voltage was recorded 
# df: dataframe version of a downsampled recording. 
# NOTE: this MUST be a downsampled recording because it assumes the samples to be turned into time stamps
    # are the index. When you initially read the data in, the samples are columns. You can also just switch
    # the index and columns of the original data to use this if you want to use it on not downsampled data
# samples: df.shape[0]
# sample_rate: 30,000 for the silicone probe recordings
# current_time: if the first part of the recording then current_time = 0; else current_time = allData.index[-1] 
# alpha = the factor by which the data was downsampled by. 
    # For example, if you went from 30,000 Hz to 128 Hz, alpha = 234 
def samples_to_seconds(df, samples, sampling_rate, current_time, alpha):    
    # number of seconds in the recording batch =
    # the sampling rate is lower by the factor of the factor used to downsample
    secs = samples/(sampling_rate/alpha)
    print("Total Time (sec):", secs)
    
    # get step size for making the new column labels corresponding to time in seconds = 
    sample_interval = secs/samples
    print("Sample Interval:", sample_interval)

    new_index = np.arange(0, samples)
    df.index = current_time + (new_index * sample_interval)
    
    return df


# Downsample & concatenate data from every file to get the total data from one recording session
# folder_path: path to the directory/folder where all the files you want to extract data from are
# file_type: the file extension of the data files. (like .rhd)
# alpha: the factor by which you want to downsample the data. 
    # For example, if you went from 30,000 Hz to 128 Hz, alpha = 234 
def loadRecording(folder_path, file_type, alpha):
    allData = [];
    counter = 1;
    current_time = 0

    for file_path in glob.glob(os.path.join(folder_path, f"*{file_type}")):
        print("\n\nFile", counter, ":" ,file_path)
        # read in data
        data = intan.read_data(file_path) 
        df = pd.DataFrame(data['amplifier_data'])
    
        # downsampling to make data more manageable
        dd_data = direct_downsample(df, alpha)
        
        # converting samples to seconds
        dd_data_df = pd.DataFrame(dd_data)
        
        if counter != 1: current_time = allData.index[-1] 
        dd_data_sec = samples_to_seconds(dd_data_df, dd_data_df.shape[0], 30000, current_time, alpha)
    
        # append the processed data to the overall storage array that will be returned
        # if it's the first file in the folder, initialize the processed data storage df, allData
        if counter == 0: 
            allData = np.empty((0, dd_data_sec.shape[1]))
        allData = pd.concat([pd.DataFrame(allData), dd_data_sec])
    
        counter = counter + 1

    return allData


# labels every record/row in the data as non-seizure (class=0), pre-seizure(class=1), or seizure(class=2)
# allData: all the data you want labeled. The index of the dataframe must be the timestamps (seconds)
# stars: an array of all the timestamps that seizures started (seconds)
# ends: an array of all the timestamps that seizurses stopped (the timestamp of the final SWD trough) (in seconds)
# return: an array the same length as the number of rows of allData that holds the class label for every row
def label_data(allData, starts, ends, sec_pre_ictal):
    allData["class"] = np.zeros(allData.shape[0], int)
    for i in range(np.shape(ends)[0]):
        allData.loc[(allData.index >= (starts[i][0]-sec_pre_ictal)) & (allData.index < starts[i][0]),"class"] = 1
        allData.loc[(allData.index >= starts[i][0]) & (allData.index < ends[i][0]), "class"] = 2

# Description:
# Sections dataset into windows of user defined size and separation from each other and then creates labels for each section.
# The chosen label is defined as the class mode of the samples in the window. 
# Then a 3rd dimension is added to allData that keeps track of which window each records is a part of
# Returns: numpy array of window labels and a 3d array that's allData + window block marker/groupings/counter
# Parameters:
# allData: the whole (downsampled) dataset you want to make window labels for.
    # The last column in this dataset MUST be "class" with the class labels for each record
# window_size: how long in seconds you want each window to be
# step_size: how many records to move ahead when making the next window
# data_hz: the sample/sec sampling freqency of the (downsampled) dataset
def windows(allData, window_size, data_hz, step_size):
    samples_per_window = data_hz * 5
    
    iters = (len(allData) - samples_per_window) // step_size + 1
    
    allData_labels_1d = np.zeros(len(allData))
    window_labels =[]
    counter = 0
    for start in range(0, len(allData) - samples_per_window + 1, step_size):
        end = start + window_size

        label = allData.iloc[start:end, -1].mode()[0]
        # create "answer" y vector
        window_labels.append(label)

        # create 1D vector with same length as allData to create a 3rd dimension for allData (after this loop finishes)
        allData_labels_1d[start:end] = counter
        counter = counter + 1

    # add 3rd dimension to allData that keeps track of which labeled block each sample is in
    # make the 1D vector 2D (each element in the 1D vector becomes it's own row)
    allData_labels_2d = np.expand_dims(allData_labels_1d, axis=1)

    # make the number of columns in new 2D vector match the number of columns in allData by copying the single element in each
    # row currently, as many times as needed.
    allData_labels_expanded = np.repeat(allData_labels_2d, allData.shape[1], axis=1)

    # now can add the window number to allData as a 3rd dimension
    allData_3d = np.dstack((allData, allData_labels_expanded))

    return window_labels, allData_3d