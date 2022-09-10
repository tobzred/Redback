""" Redback Inverter library, for download of cloud portal data """

from datetime import (datetime, timedelta)
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
from json.decoder import JSONDecodeError

class RedbackError(Exception):
    """ Redback Inverter error """
    pass

class RedbackInverter:
    """ Gather Redback Inverter data from the cloud API """
    
    serial = None
    _apiBaseURL = 'https://portal.redbacktech.com/api/v2/'
    _apiCookie = ''
    _apiResponse = 'json'
    _inverterInfo = None
    _energyData = None
    _energyDataUpdateInterval = timedelta(minutes=1)
    _energyDataNextUpdate = datetime.now()

    def __init__(self, cookie, serial):
        """ Constructor: needs API auth cookie and inverter serial number """

        self.serial = serial
        self._apiSerial = '?SerialNumber=' + serial
        self._apiCookie = cookie

    def _apiRequest(self, apimethod):
        """ Call into Redback cloud API """

        if (apimethod == 'energyflowd2'):
            # https://portal.redbacktech.com/api/v2/energyflowd2/$SERIAL
            full_url = self._apiBaseURL + apimethod + '/' + self.serial
        else:
            # https://portal.redbacktech.com/api/v2/inverterinfo?SerialNumber=$SERIAL
            full_url = self._apiBaseURL + apimethod + self._apiSerial

        request = Request(full_url)
        request.add_header('Cookie', self._apiCookie)

        try:
            response = urlopen(request)
        except HTTPError as e:
            raise RedbackError(f'HTTP Error. {e.code} {e.reason} (Has the .AspNet.ApplicationCookie expired?)')
        except URLError as e:
            raise RedbackError(f'URL Error. {e.reason}')

        # collect data packet
        try:
            data = json.loads( response.read() )
        except JSONDecodeError as e:
            raise RedbackError(f'JSON Error. {e.msg}. Pos={e.pos} Line={e.lineno} Col={e.colno}')

        return data

    def getInverterInfo(self):
        """ Returns inverter info (static data, updated first use only) """

        if (self._inverterInfo == None):
            self._inverterInfo = self._apiRequest('inverterinfo')
            bannerInfo = self._apiRequest('BannerInfo')
            self._inverterInfo['ProductDisplayname'] = bannerInfo['ProductDisplayname']
            self._inverterInfo['InstalledPvSizeWatts'] = bannerInfo['InstalledPvSizeWatts']
            self._inverterInfo['BatteryCapacityWattHours'] = bannerInfo['BatteryCapacityWattHours']

        # keys: Model, Firmware, RossVersion, IsThreePhaseInverter, IsSmartBatteryInverter, IsSinglePhaseInverter, IsGridTieInverter, ProductDisplayname, InstalledPvSizeWatts, BatteryCapacityWattHours
        return self._inverterInfo

    def getEnergyData(self):
        """ Returns energy data (dynamic data, instantaneous with 60s resolution) """

        # energy data in the cloud data store is only refreshed by the Ouija device every 60s
        if (datetime.now() > self._energyDataNextUpdate or self._energyData == None):
            self._energyData = self._apiRequest('energyflowd2')['Data']['Input']
            self._energyDataNextUpdate = datetime.now() + self._energyDataUpdateInterval

        # keys: ACLoadW, BackupLoadW, SupportsConnectedPV, PVW, ThirdPartyW, GridStatus, GridNegativeIsImportW, ConfiguredWithBatteries, BatteryNegativeIsChargingW, BatteryStatus, BatterySoC0to100, CtComms
        return self._energyData

