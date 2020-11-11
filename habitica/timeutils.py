import datetime, time

class LocalTZ(datetime.tzinfo):
    """ Current local timezone. """
    STDOFFSET = datetime.timedelta(seconds = -time.timezone)
    DSTOFFSET = datetime.timedelta(seconds = -time.altzone) if time.daylight else STDOFFSET
    DSTDIFF = DSTOFFSET - STDOFFSET
    def utcoffset(self, dt):
        if self._isdst(dt):
            return LocalTZ.DSTOFFSET
        else:
            return LocalTZ.STDOFFSET
    def dst(self, dt):
        if self._isdst(dt):
            return LocalTZ.DSTDIFF
        else:
            return datetime.timedelta(0)
    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]
    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0

def strptime_habitica_to_local(time_string):
    ''' Habitica's task start time is in GMT (apparently?)
    so it needs to be converted to local TZ before calculating any task repetition.
    '''
    return datetime.datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=datetime.timezone.utc).astimezone(LocalTZ())

def parse_isodate(isodate):
    """ Parses date string in ISO format. """
    return datetime.datetime.strptime(isodate, "%Y-%m-%d %H:%M:%S.%f")

def days_passed(habitica_startDate, localnow, timezoneOffset=0):
    """
    Calculates number of full days passed between task start date (GMT) and now (local).
    Timezone offset is in full minutes (relative to GMT),
    should be taken from user's preferences (API /user[preferences][timezoneOffset])
    """
    #startdate = strptime_habitica_to_local(habitica_startDate)
    startdate = datetime.datetime.strptime(habitica_startDate, '%Y-%m-%dT%H:%M:%S.%fZ')
    startdate -= datetime.timedelta(minutes=timezoneOffset)
    currentdate = localnow
    return (currentdate.date() - startdate.date()).days
