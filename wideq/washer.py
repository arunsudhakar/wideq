import enum
from typing import Optional

from .client import Device
from .util import lookup_enum, lookup_reference


class WasherState(enum.Enum):
    """The state of the washer device."""

    NA    = "-"    
    SPIN_NS    = "@WM_OPTION_SPIN_NO_SPIN_W"    
    SPIN_400   = "@WM_OPTION_SPIN_400_W"    
    SPIN_600   = "@WM_OPTION_SPIN_600_W"    
    SPIN_800   = "@WM_OPTION_SPIN_800_W"    
    SPIN_1000  = "@WM_OPTION_SPIN_1000_W"    
    SPIN_1200  = "@WM_OPTION_SPIN_1200_W"    
    SPIN_1400  = "@WM_OPTION_SPIN_1400_W"    
    SPIN_1600  = "@WM_OPTION_SPIN_1600_W"    

    SOIL_LIGHT = "@WM_OPTION_SOIL_LIGHT_W"
    SOIL_NORMAL = "@WM_OPTION_SOIL_NORMAL_W"
    SOIL_HEAVY = "@WM_OPTION_SOIL_HEAVY_W"

    WTEMP_COLD = "@WM_OPTION_TEMP_COLD_W"
    WTEMP_20   = "@WM_OPTION_TEMP_20_W"
    WTEMP_30   = "@WM_OPTION_TEMP_30_W"
    WTEMP_40   = "@WM_OPTION_TEMP_40_W"
    WTEMP_60   = "@WM_OPTION_TEMP_60_W"
    WTEMP_95   = "@WM_OPTION_TEMP_95_W"

    RINSE_NORMAL  = "@WM_OPTION_RINSE_NORMAL_W"
    RINSE_RINSEP  = "@WM_OPTION_RINSE_RINSE+_W"
    RINSE_RINSEPP = "@WM_OPTION_RINSE_RINSE++_W"
    RINSE_NHOLD   = "@WM_OPTION_RINSE_NORMALHOLD_W"
    RINSE_RINSEHOLD = "@WM_OPTION_RINSE_RINSE+HOLD_W"

    ADD_DRAIN = '@WM_STATE_ADD_DRAIN_W'
    COMPLETE = '@WM_STATE_COMPLETE_W'
    DETECTING = '@WM_STATE_DETECTING_W'
    DETERGENT_AMOUNT = '@WM_STATE_DETERGENT_AMOUNT_W'
    DRYING = '@WM_STATE_DRYING_W'
    END = '@WM_STATE_END_W'
    ERROR_AUTO_OFF = '@WM_STATE_ERROR_AUTO_OFF_W'
    FRESH_CARE = '@WM_STATE_FRESHCARE_W'
    FROZEN_PREVENT_INITIAL = '@WM_STATE_FROZEN_PREVENT_INITIAL_W'
    FROZEN_PREVENT_PAUSE = '@WM_STATE_FROZEN_PREVENT_PAUSE_W'
    FROZEN_PREVENT_RUNNING = '@WM_STATE_FROZEN_PREVENT_RUNNING_W'
    INITIAL = '@WM_STATE_INITIAL_W'
    OFF = '@WM_STATE_POWER_OFF_W'
    PAUSE = '@WM_STATE_PAUSE_W'
    PRE_WASH = '@WM_STATE_PREWASH_W'
    RESERVE = '@WM_STATE_RESERVE_W'
    RINSING = '@WM_STATE_RINSING_W'
    RINSE_HOLD = '@WM_STATE_RINSE_HOLD_W'
    RUNNING = '@WM_STATE_RUNNING_W'
    SMART_DIAGNOSIS = '@WM_STATE_SMART_DIAG_W'
    SMART_DIAGNOSIS_DATA = '@WM_STATE_SMART_DIAGDATA_W'
    SPINNING = '@WM_STATE_SPINNING_W'
    TCL_ALARM_NORMAL = 'TCL_ALARM_NORMAL'
    TUBCLEAN_COUNT_ALARM = '@WM_STATE_TUBCLEAN_COUNT_ALRAM_W'


class WasherDevice(Device):
    """A higher-level interface for a washer."""

    def poll(self) -> Optional['WasherStatus']:
        """Poll the device's current state.

        Monitoring must be started first with `monitor_start`.

        :returns: Either a `WasherStatus` instance or `None` if the status is
            not yet available.
        """
        # Abort if monitoring has not started yet.
        if not hasattr(self, 'mon'):
            return None

        data = self.mon.poll()
        if data:
            return self.model.decode_monitor(data)
        else:
            return None

class WasherStatus(object):
    """Higher-level information about a washer's current status.

    :param washer: The WasherDevice instance.
    :param data: JSON data from the API.
    """

    def __init__(self, washer: WasherDevice, data: dict):
        self.washer = washer
        self.data = data

    @property
    def state(self) -> WasherState:
        """Get the state of the washer."""
        return WasherState(lookup_enum('State', self.data, self.washer))

    @property
    def previous_state(self) -> WasherState:
        """Get the previous state of the washer."""
        return WasherState(lookup_enum('PreState', self.data, self.washer))

    @property
    def spinspeed(self) -> WasherState:
        """Get the spin speed of the washer."""
        return WasherState(lookup_enum('SpinSpeed', self.data, self.washer))

    @property
    def watertemp(self) -> WasherState:
        """Get the water temp of the washer."""
        return WasherState(lookup_enum('WaterTemp', self.data, self.washer))

    @property
    def rinseoption(self) -> WasherState:
        """Get the rinse option of the washer."""
        return WasherState(lookup_enum('RinseOption', self.data, self.washer))

#'Course': '0', 'Error': '0', 'Soil': '0', 'SpinSpeed': '0', 'WaterTemp': '0', 'RinseOption': '0', 'DryLevel': '0', 'Reserve_Time_H': '0', 'Reserve_Time_M': '0', 'Option1': '0', 'Option2': '132', 'Option3': '0', 'PreState': '22', 'SmartCourse': '0', 'TCLCount': '34', 'LoadItem': '0', 'CourseType': '0', 'Standby': '1'}}

    @property
    def is_on(self) -> bool:
        """Check if the washer is on or not."""
        return self.state != WasherState.OFF

    @property
    def remaining_time(self) -> int:
        """Get the remaining time in minutes."""
        return (int(self.data['Remain_Time_H']) * 60 +
                int(self.data['Remain_Time_M']))

    @property
    def initial_time(self) -> int:
        """Get the initial time in minutes."""
        return (
            int(self.data['Initial_Time_H']) * 60 +
            int(self.data['Initial_Time_M']))

    def _lookup_reference(self, attr: str) -> str:
        """Look up a reference value for the provided attribute.

        :param attr: The attribute to find the value for.
        :returns: The looked up value.
        """
        value = self.washer.model.reference_name(attr, self.data[attr])
        if value is None:
            return 'Off'
        return value

    @property
    def course(self) -> str:
        """Get the current course."""
        return lookup_reference('Course', self.data, self.washer)

    @property
    def smart_course(self) -> str:
        """Get the current smart course."""
        return lookup_reference('SmartCourse', self.data, self.washer)

    @property
    def error(self) -> str:
        """Get the current error."""
        return lookup_reference('Error', self.data, self.washer)

    def __str__(self):
        return str(self.__class__) + ": " + str(self.__dict__)
