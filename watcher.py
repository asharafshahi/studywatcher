
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

def moveAndCallProxy(dcm_path):
	studyUID = os.path.split(dcm_path)[1][2:]
	dest_path = os.path.join(dest_dir,studyUID)
	if os.path.exists(dest_path):
		try:
			shutil.rmtree(dest_path)
		except Exception as e:
	        	print(e)

	studyFolder = shutil.move(dcm_path, dest_path)
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

def deleteContents(folderPath):
	for item in os.listdir(folderPath):
	    item_path = os.path.join(folderPath, item)
	    try:
	        if os.path.isfile(item_path): os.unlink(item_path)
	        elif os.path.isdir(item_path): shutil.rmtree(item_path)
	    except Exception as e:
	        print(e)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    input_dir = config['DEFAULT']['input_dir']
    dest_dir = config['DEFAULT']['dest_dir']
    proxy_endpoint_url = config['DEFAULT']['proxy_endpoint']
    poll_time = int(config['DEFAULT']['poll_time'])
    study_complete_timout = int(config['DEFAULT']['study_complete_timeout'])

    # clear out outgoing directory to avoid errors and easily handle garbage clean up
    deleteContents(dest_dir)

    print('Checking {} for new incoming DICOM files every {} seconds and calling proxy endpoint {}'.format(input_dir,
			poll_time, proxy_endpoint_url))

    # Start a timer to process the incoming directory after a 10 second delay
    s = sched.scheduler(time.time, time.sleep)
    s.enter(poll_time, 1, processReceivedStudies, (s, ))
    s.run()
