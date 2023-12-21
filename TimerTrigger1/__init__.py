import datetime
import logging
import asyncio
import aiohttp
import json
import time
import os
import re
import logging

import azure.functions as func

from .state_manager_async import StateManagerAsync
from .sentinel_connector_async import AzureSentinelMultiConnectorAsync

logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)

WORKSPACE_ID = os.environ['AzureSentinelWorkspaceId']
SHARED_KEY = os.environ['AzureSentinelSharedKey']
API_URL = os.environ['CortexXDRAPIUrl']
USER = os.environ['CortexXDRAccessKeyID']
PASSWORD = os.environ['CortexXDRSecretKey']
FILE_SHARE_CONN_STRING = os.environ['AzureWebJobsStorage']
AUDIT_LOG_TYPE = 'PaloAltoSentinel'
LOGTYPE = os.environ.get('LogType',"audit")

# if ts of last event is older than now - MAX_PERIOD_MINUTES -> script will get events from now - MAX_PERIOD_MINUTES
MAX_PERIOD_MINUTES = 60 * 6

LOG_ANALYTICS_URI = os.environ.get('logAnalyticsUri')

if not LOG_ANALYTICS_URI or str(LOG_ANALYTICS_URI).isspace():
    LOG_ANALYTICS_URI = 'https://' + WORKSPACE_ID + '.ods.opinsights.azure.com'

pattern = r'https:\/\/([\w\-]+)\.ods\.opinsights\.azure.([a-zA-Z\.]+)$'
match = re.match(pattern, str(LOG_ANALYTICS_URI))
if not match:
    raise Exception("Invalid Log Analytics Uri.")


async def main(mytimer: func.TimerRequest):
    logging.info('Script started.')
    async with aiohttp.ClientSession() as session:
        async with aiohttp.ClientSession() as session_sentinel:
            prisma = PaloAltoCloudConnector(API_URL, USER, PASSWORD, session=session, session_sentinel=session_sentinel)

            tasks = []

            logging.info('LOGTYPE value : {}'.format(LOGTYPE))
            if LOGTYPE.lower().__contains__('audit') :
                tasks.append(prisma.process_audit_logs())

            await asyncio.gather(*tasks)

    logging.info('Program finished. {} events have been sent.'.format(prisma.sentinel.successfull_sent_events_number))


class PaloAltoCloudConnector:
    def __init__(self, api_url, username, password, session: aiohttp.ClientSession, session_sentinel: aiohttp.ClientSession):
        self.api_url = api_url
        self.__username = username
        self.__password = password
        self.session = session
        self.session_sentinel = session_sentinel
        self._token = None
        self._auth_lock = asyncio.Lock()
      #  self.alerts_state_manager = StateManagerAsync(FILE_SHARE_CONN_STRING, share_name='paloaltocloudsentinel', file_path='prismacloudlastalert')
        self.auditlogs_state_manager = StateManagerAsync(FILE_SHARE_CONN_STRING, share_name='paloaltocloudsentinel', file_path='paloaltocloudlastauditlog')
        self.sentinel = AzureSentinelMultiConnectorAsync(self.session_sentinel, LOG_ANALYTICS_URI, WORKSPACE_ID, SHARED_KEY, queue_size=10000)
        #self.sent_alerts = 0
        self.sent_audit_logs = 0
        #self.last_alert_ts = None
        self.last_audit_ts = None

    async def process_audit_logs(self):
        last_log_ts_ms = await self.auditlogs_state_manager.get()
        max_period = (int(time.time()) - MAX_PERIOD_MINUTES * 60) * 1000
        if not last_log_ts_ms or int(last_log_ts_ms) < max_period:
            log_start_ts_ms = max_period
            logging.info('Last audit log was too long ago or there is no info about last log timestamp.')
        else:
            log_start_ts_ms = int(last_log_ts_ms) + 1
        logging.info('Starting searching audit logs from {}'.format(log_start_ts_ms))

        async for event in self.get_audit_logs(start_time=log_start_ts_ms):
            if not last_log_ts_ms:
                last_log_ts_ms = event['timestamp']
            elif event['timestamp'] > int(last_log_ts_ms):
                last_log_ts_ms = event['timestamp']
            await self.sentinel.send(event, log_type=AUDIT_LOG_TYPE)
            self.sent_audit_logs += 1

        self.last_audit_ts = last_log_ts_ms

        conn = self.sentinel.get_log_type_connector(AUDIT_LOG_TYPE)
        if conn:
            await conn.flush()
            logging.info('{} audit logs have been sent'.format(self.sent_audit_logs))
        await self.save_audit_sentinel()



    async def get_audit_logs(self, start_time):
        await self._authorize()
        uri = self.api_url 
        headers = {
            'x-redlock-auth': self._token,
            "Accept": "*/*",
            "Content-Type": "application/json"
        }

        unix_ts_now = (int(time.time()) - 10) * 1000
        params = {
            'timeType': 'absolute',
            'startTime': start_time,
            'endTime': unix_ts_now
        }
        async with self.session.get(uri, headers=headers, params=params) as response:
            if response.status != 200:
                raise Exception('Error while getting audit logs. HTTP status code: {}'.format(response.status))
            res = await response.text()
            res = json.loads(res)

        for item in res:
            yield item


    async def save_audit_sentinel(self):
        if self.last_audit_ts:
            await self.auditlogs_state_manager.post(str(self.last_audit_ts))
            logging.info('Last audit ts saved - {}'.format(self.last_audit_ts))
