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

def moveAndCallProxy(dcm_path):
	studyUID = os.path.split(dcm_path)[1][2:]
	studyFolder = shutil.move(dcm_path, os.path.join(dest_dir,studyUID))
	print('Invoking proxy with study UID {}'.format(studyUID)) 
	proxy_payload = {
					'studyUID': studyUID,
					'studyFolder': studyFolder
					}
	try:
		r = requests.post(proxy_endpoint_url, data=json.dumps(proxy_payload))
		if (r.status_code == 200):
			print('Study {} successfully submitted to proxy'.format(dcm_path))
		else:
			print('Received status code {} from the proxy'.format(r.status_code))
	
	except requests.exceptions.RequestException as e:	
		print('Failed to connect to Proxy.')	

def processReceivedStudies(sc):
    incoming_studies = {}  # dictionary object to track what new studies are coming in and need to be cleaned up
    study_dirs = [os.path.join(input_dir, d) for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))]
    for study in study_dirs:
        incoming_studies[study] = os.path.getmtime(max(glob.glob(os.path.join(study, '*.dcm')), key=os.path.getctime))
		
    print('Found {} studies in directory'.format(len(study_dirs)))

    for study in incoming_studies:
        # check each found study to see if the last changed file was changed more than X seconds ago, meaning we can start processing
        if (datetime.datetime.now() - datetime.datetime.fromtimestamp(incoming_studies[study])) > datetime.timedelta(seconds = study_complete_timout):
            print('Study {} has been complete for more than 10 seconds. Moving and calling Proxy.'.format(study))
            moveAndCallProxy(study)

    # restart the timer to repeat in 10 seconds
    sc.enter(poll_time, 1, processReceivedStudies, (sc,))
		
			
if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    input_dir = config['DEFAULT']['input_dir']
    dest_dir = config['DEFAULT']['dest_dir']
    proxy_endpoint_url = config['DEFAULT']['proxy_endpoint']
    poll_time = int(config['DEFAULT']['poll_time'])
    study_complete_timout = int(config['DEFAULT']['study_complete_timeout'])
	
	
    print('Checking {} for new incoming DICOM files every {} seconds and calling proxy endpoint {}'.format(input_dir, 
			poll_time, proxy_endpoint_url))

    # Start a timer to process the incoming directory after a 10 second delay
    s = sched.scheduler(time.time, time.sleep)
    s.enter(poll_time, 1, processReceivedStudies, (s, ))
    s.run()
	
	

