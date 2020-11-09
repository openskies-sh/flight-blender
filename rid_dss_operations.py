## A module to read data from a DSS, this specifically implements the Remote ID standard as released on Oct-2020
## For more information review: https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/uastech/standards/astm_rid_1.0/remoteid/canonical.yaml 
## and this diagram https://github.com/interuss/dss/blob/master/assets/generated/rid_display.png

from functools import wraps
import json
from __main__ import app
from flask_uuid import FlaskUUID
from six.moves.urllib.request import urlopen
from auth import AuthError, requires_auth, requires_scope
import redis
from datetime import datetime, timedelta
import uuid
import requests
from os import environ as env

REDIS_HOST = os.getenv('REDIS_HOST',"redis")
REDIS_PORT = 6379

class AuthorityCredentialsGetter():
    ''' All calls to the DSS require credentials from a authority, usually the CAA since they can provide access to the system '''
    def __init__(self):
        pass
        
    def get_cached_credentials(self, audience):  
        r = redis.Redis()
        
        now = datetime.now()
        cache_key = audience + '_auth_dss_token'
        token_details = r.get(cache_key)
        if token_details:    
            token_details = json.loads(token_details)
            created_at = token_details['created_at']
            set_date = datetime.strptime(created_at,"%Y-%m-%dT%H:%M:%S.%f")
            if now < (set_date - timedelta(minutes=58)):
                credentials = self.get_read_credentials(audience)
                r.set(cache_key, json.dumps({'credentials': credentials, 'created_at':now.isoformat()}))
            else: 
                credentials = token_details['credentials']
        else:               
            credentials = self.get_read_credentials(audience)
            r.set(cache_key, json.dumps({'credentials': credentials, 'created_at':now.isoformat()}))            
            r.expire(cache_key, timedelta(minutes=58))
            
        return credentials
            
        
    def get_read_credentials(self, audience):        
        payload = {"grant_type":"client_credentials","client_id": env.get('AUTH_DSS_CLIENT_ID'),"client_secret": env.get('AUTH_DSS_CLIENT_SECRET'),"audience":audience,"scope": 'dss.read_identification_service_areas'}        
        url = env.get('DSS_AUTH_URL') + env.get('DSS_AUTH_TOKEN_URL')        
        token_data = requests.post(url, data = payload)
        t_data = token_data.json()        
        return t_data

class RemoteIDOperations():

    def __init__(self):
        self.dss_base_url = env.get('DSS_BASE_URL')

    def submit_dss_subscription(self, vertex_list):
        ''' This method PUTS /dss/subscriptions ''' 

        new_subscription_id = str(uuid.uuid4())
        dss_subscription_url = self.dss_base_url + '/dss/subscriptions/' + new_subscription_id

        callback_url = "https://example.com/identification_service_areas" # TODO: Fix to have the actual URL
        current_time = datetime.now().isoformat()
        one_hour_from_now = (datetime.now() + timedelta(hours=1)).isoformat()
        headers = {'content-type': 'application/json'}
        
        volume_object = {"spatial_volume":{"footprint":{"vertices":vertex_list},"altitude_lo":19.5,"altitude_hi":19.5},"time_start":current_time,"time_end":one_hour_from_now}

        payload = {"extents": volume_object, "callbacks":{"identification_service_area_url":callback_url}}

        r = requests.post(dss_subscription_url, data= json.dumps(payload), headers=headers,auth=(self.COUCHDB_USERNAME, self.COUCHDB_PASSWORD))
        
        try: 
            assert r.status_code == 200
        except AssertionError as ae: 
            return {"subscription_id": 0, "notification_index": 0}
        else: 	
            dss_response = r.json()
            service_areas = dss_response['service_areas']
            subscription = dss_response['subscription']
            notification_index = subscription['notification_index']
            # iterate over the service areas to get flights URL to poll 
            flights_url_list = []
            for service_area in service_areas: 
                flights_url = service_area['flights_url']
                flights_url_list.append(flights_url)
                
            redis = redis.Redis()
            redis.hmset("all_uss_flights", flights_url_list)
                

        # process DSS repsonse
        # store the subscription id and notificaiton index (might be handy)
        # parse the service_area list 
        # store service area id and flights url
        # poll the flights URL every 3 seconds

    def delete_dss_subscription(self,subscription_id):
        ''' This module calls the DSS to delete a subscription''' 

        # TODO: Make this a loop / 1s updated (make it a task)
        # get credentials with appropriate audience 
        # send GET to USS flight url /uss/flights/{id}/details

        pass



@requires_auth
@app.route("/subscribe_to_dss", methods=['POST'])
def subscribe_to_dss(vertex_list):
    ''' This module takes a lat, lng box from Flight Spotlight and puts in a subscription to the DSS for the ISA '''


    return 'it works!'



