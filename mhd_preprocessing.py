import sys
import glob
import datetime
import sched, time
import os.path
import shutil
import configparser
import json
import requests
import SimpleITK as sitk

def convertDCMtoMHD(dcm_path, mhd_path, deleteDCM=False):
    reader = sitk.ImageSeriesReader()
    series_found = reader.GetGDCMSeriesIDs(dcm_path)
    print('Found {} series'.format(len(series_found)))
    series_len = 0
    final_dcm_names = []
    final_series_name = ''
    if len(series_found):
        for series in series_found:
            dcm_names = reader.GetGDCMSeriesFileNames(dcm_path, series)
            print('Found series {} with {} images.'.format(series, len(dcm_names)))
            if len(dcm_names) > series_len:
                final_dcm_names = dcm_names
                final_series_name = series
                series_len = len(dcm_names)
        print('Writing series with {} images to .mhd file'.format(len(final_dcm_names)))
        reader.SetFileNames(final_dcm_names)
        image = reader.Execute()
        sitk.WriteImage(image, os.path.join(mhd_path, final_series_name + '.mhd'))
        print('Image size: {}'.format(image.GetSize()))

    if deleteDCM:
        shutil.rmtree(dcm_path)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('This pre-processing script requires two command line arguments.')
        print('Usage: mhd_preprocessing.py <source_path> <dest_path>')
        sys.exit()

    convertDCMtoMHD(sys.argv[1], sys.argv[2], True)
