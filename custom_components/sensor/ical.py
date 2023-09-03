"""
Support for iCal-URLs

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.ical/
"""
import logging
from datetime import timedelta

#import voluptuous as vol

import datetime as dt
from datetime import *
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import STATE_UNKNOWN, CONF_NAME
import homeassistant.helpers.config_validation as cv
import voluptuous as vol



DOMAIN='group_avaerage'
DEFAULT_NAME="GROUPING"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})



import icalendar, requests, arrow


_LOGGER = logging.getLogger(__name__)
REQUIREMENTS = ['icalendar', 'requests', 'arrow>=0.10.0']

ICON = 'mdi:calendar'
DEFAULT_NAME = 'iCal Sensor'
DEFAULT_MAX_EVENTS = 5
DOMAIN = 'ical'

# Return cached results if last scan was less then this time ago.
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=120)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the iCal Sensor."""
    url = config.get('url')
    SNS_PREFIX = config.get("prefix", "sensor")
    name = config.get('name', DEFAULT_NAME)
    mp = config.get("map")
    if mp is not None: 
        mp = list(mp)
    maxevents = config.get('maxevents',DEFAULT_MAX_EVENTS)

    if url is None:
        _LOGGER.error('Missing required variable: "url"')
        return False

    data_object = ICalData(url)
    data_object.update()

    if data_object.data is None:
        _LOGGER.error('Unable to fetch iCal')
        return False

    sensors = []
    for eventnumber in range(maxevents):
        sensors.append(ICalSensor(hass,data_object,eventnumber, SNS_PREFIX, mp))

    add_devices(sensors)

    # add_devices_callback([ICalSensor(hass, data_object,name)])
    return True


def dateparser(calendar,date):
    events = []
    for event in calendar.walk('VEVENT'): 
        if type(event['DTSTART'].dt) is dt.date:
            start = arrow.get(event['DTSTART'].dt)
            start = start.replace(tzinfo='local')
        else: start = event['DTSTART'].dt
        if type(event['DTEND'].dt) is dt.date:
            end = arrow.get(event['DTEND'].dt)
            end = end.replace(tzinfo='local')
        else: end = event['DTEND'].dt
        if start.date() >= date.date():
            events.append(dict(name=event['SUMMARY'],begin=start))
    sorted_events = sorted(events, key=lambda k: k['begin'])
    _LOGGER.info(sorted_events)
    return sorted_events

# pylint: disable=too-few-public-methods
class ICalSensor(Entity):
    """Implementation of a iCal sensor."""
    def __init__(self, hass, data_object, eventnumber,SNS_PREFIX, mp):
        """Initialize the sensor."""
        self._eventno = eventnumber
        self._hass = hass
        self._days = 1000
        self._pickup_type = data_object.data[eventnumber]['name']
        self.data_object = data_object
        self._name = SNS_PREFIX + str(eventnumber)
        self._entity_id = 'sensor.'+SNS_PREFIX + str(eventnumber)
        self.entity_id = 'sensor.'+SNS_PREFIX + str(eventnumber)
        self.object_id = 'sensor.'+SNS_PREFIX + str(eventnumber)
        self._icn = "help-circle-outline"
        self.ma = mp

        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._friendly_name

    @property
    def icon(self):
        """Return the icon for the frontend."""
        return ICON

    @property
    def state(self):
        """Return the date of the next event."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        attr = {}
        attr['friendly_name'] = self._friendly_name
        attr['pickup_type'] = self._pickup_type
        attr['icon'] = self._icn
        attr['days'] = self._days
        #attr[ATTR_ATTRIBUTION] = CONF_ATTRIBUTION
        return attr


    def update(self):
        """Get the latest update and set the state."""
        self.data_object.update()
        e = self.data_object.data
        if self._eventno not in range(0,len(e)):
            self._state = "No event"
        else:
            if not e:
                self._state = "No event"
            else:
                val = e[self._eventno]
                #self._name = val['name']
                #self._friendlyname = val['name']
                #self._name = val['name']
                # glass = glass-tulip
                # recycling = recycle
                # food = food
                # general = delete
                # garden = nature
                # default = help-circle-outline
                #if ! map is none:
                icon = "help-circle-outline"
                t = val["name"]
                mp = self.ma
                if mp is not None:
                    for m in mp:
                        if m["value"] in val['name']:
                            icon = m['icon']
                            t = m['name']

#                    if "Food caddy" in val['name']:
#                        icon = "food"
#                        t = "Grey - food Bin"
#                    if "Blue recycling bin" in val['name']:
#                        icon = "recycle"
#                        t = "Blue - recycling Bin"
#                    if "Brown garden bin" in val['name']:
#                        icon = "nature"
#                        t = "Brown - garden bin"
#                    if "Green refuse" in val['name']:
#                        icon = "delete"
#                        t = "Green - refuse Bin"
#                    if "Black box" in val['name']:
#                        icon = "glass-tulip"
#                        t = "Black - glass and electronics Bin"




                self._icn = "mdi:" + icon
                self._pickup_type = t
                self.friendly_name = t
                self._friendly_name = t
                
                today = date.today()
                year =  int(val['begin'].strftime("%Y"))
                month =  int(val['begin'].strftime("%-m"))
                day =  int(val['begin'].strftime("%-d"))
                currentlyis = today.strftime("%a");
                future = date(year,month,day)
                v = int((future - today).days)
                output = ''      
                currentdayindice = int(date.today().strftime("%w"))
                if v == 0:
                    output = "Today"
                if v == 1:
                    output = "Tommorrow"
                w = currentdayindice + v
                currentdayindice = int(date.today().strftime("%w"))
                onday = future.strftime("%A")
                if v >= 2:
                    output = '' 
                    dayarr = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                    dow = (7-currentdayindice)+v+2
                    
                    while dow >= 7:
                        dow = dow - 7
                    output = "{}".format(onday)
                    #output = dow
                if v >= 7:
                    s = ''
                    if v >= 14: 
                        s = "s"
                    output = "{} week{} from {} ".format(int(v/7), s, onday)
                self._state = output
                self._days = v


                #self._state = (future - today).days

                #self._state = val['begin'].strftime("%-d %B %Y")
                #self._state = "{} - {}".format( val['name'], val['begin'].strftime("%-d %B %Y"))

#pylint: disable=too-few-public-methods
class ICalData(object):
    """Class for handling the data retrieval."""

    def __init__(self, resource):
        self._request = requests.Request('GET', resource).prepare()
        self.data = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        self.data = []

        try:
            with requests.Session() as sess:
                response = sess.send(self._request, timeout=10)

            cal = icalendar.Calendar.from_ical(response.text)
            today = arrow.utcnow()
            events = dateparser(cal,today)

            self.data = events

        except requests.exceptions.RequestException:
            _LOGGER.error("Error fetching data: %s", self._request)
            self.data = None