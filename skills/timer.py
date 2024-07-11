from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import pickle
from num2words import num2words
from speech_util import speak
from utils.parsers import is_numeric, look_for_fractions, \
    invert_dict, ReplaceableNumber, partition_list, tokenize, Token, Normalizer

class AlarmSkill:
    """The official alarm skill for Willow"""

    def __init__(self):
        """Executed immediately after class is initialized"""

        # load alarm list that has been saved to disk
        with open('things/alarms.pkl', 'rb') as f:
            self.alarms : list = pickle.load(f)
        
        # Alarm list format: [ [
        #                       time alarm should ring next : datetime, 
        #                       days that the alarm recurs : set or None,
        #                       expiration date for recurring alarm : datetime or None
        #                        ], ... ]
        #
        # NOTE: I probably should have implemented each alarm as a dict instead of a list, 
        #       will fix in a future version

        # ensure list is sorted and up to date
        self.alarms.sort(key=self.sort_func)
        self.prune()

        with open('things/alarms.pkl', 'wb') as f:
            pickle.dump(self.alarms, f)
        
        # load up recurrence data (data that allows an alarm to be repeated )
        self.recurrences = ['mondays', 'tuesdays', 'wednesdays', 'thursdays', 'fridays', 'saturdays',  \
            'sundays', 'weekdays', 'workdays', 'weekends', 'each', 'every', 'daily']
        self.day_dict = {'0': 'sunday', '1': 'monday', '2': 'tuesday', '3': 'wednesday', '4': 'thursday', \
            '5': 'friday', '6': 'saturday'}
        
        with open('things/recurring') as file:
            data = file.read().replace('\n', ',')
            recurrence_list = data.split(',')
            self.recurrence_dict = {recurrence_list[i]: recurrence_list[i+1] for i in range(0, len(recurrence_list), 2)}

    def sort_func(self, e):
        """function that is passed to alarms.sort as its key to properly sort the alarm list"""
        return e[0]

    def clear_alarms(self):
        """delete all alarms"""
        self.alarms = []
        with open('things/alarms.pkl', 'wb') as f:
            pickle.dump(self.alarms, f)
    
    def print_alarms(self):
        print(self.alarms)
    
    def check_for_alarm(self):
        """determine whether an alarm is going off at this moment"""
        time = datetime.now()
        if len(self.alarms) == 0:
            return False

        return self.alarms[0][0] <= time

    def alarm_query(self, utr):
        """ Responds to user utterance that has the intent 'alarm_query' """
        data = self.extract_datetime_en(utr)

        # if user specifies a specific time
        just_alarms = [alarm[0] for alarm in self.alarms]
        if data != None:
            if data[0] in just_alarms:
                index = just_alarms.index(data[0])
                speak('yes, you have an alarm set for ' + self.datetime_to_string(data[0], self.alarms[index][1]))
                return
        
        # if there are no alarms
        num_alarms = len(self.alarms)
        if num_alarms == 0:
            speak('you dont have any alarms set')
            return
        # if there is 1 alarm total
        if num_alarms == 1:
            speak('you have an alarm set for ' + self.datetime_to_string(self.alarms[0][0], self.alarms[0][1]))
            return
        
        # if there are multiple alarms set
        response = 'you have ' + str(num_alarms) + ' alarms. they are set for '
        for i , alarm in enumerate(self.alarms):
            response += self.datetime_to_string(alarm[0], alarm[1])
            if i == len(self.alarms) - 2:
                response += ', and '
            else:
                response += ', '
        
        speak(response)

    def alarm_remove(self, utr):
        """ Handles user utterance with intent 'alarm_remove' """
        self._alarm_remove(utr)
        with open('things/alarms.pkl', 'wb') as f:
            pickle.dump(self.alarms, f)
        
    # TODO: minor edge cases have not yet been accounted for
    def _alarm_remove(self, utr):
        """ Responds to user utterance that has the intent 'alarm_remove' """
        
        if 'all' in utr or 'everything' in utr:
            speak('all alarms removed')
            self.clear_alarms()
            return

        data = self.extract_datetime_en(utr)

        # if theres a time in the user utterance, delete the alarm with that time
        just_alarms = [alarm[0] for alarm in self.alarms]
        if data != None:
            just_alarm_times = [a.time() for a in just_alarms]
            if data[0].time() in just_alarm_times:
                try:
                    index = just_alarms.index(data[0])
                except ValueError:
                    index = just_alarm_times.index(data[0].time())
                
                alarm = self.alarms[index]
                if not alarm[1]:
                    speak('removed alarm set for ' + self.datetime_to_string(alarm[0]))
                    self.alarms.remove(alarm)
                    return
                if alarm[1] and 'every' or 'all' in data[1]:
                    speak('removed alarm set for ' + self.datetime_to_string(alarm[0], alarm[1]))
                    self.alarms.remove(alarm)
                    return
                elif alarm[1]:
                    response = input('should i remove all instances of this alarm (y for yes)?')
                    if response == 'y':
                        speak('removed alarm set for' + self.datetime_to_string(alarm[0], alarm[1]))
                        self.alarms.remove(alarm)
                        return
                    else:
                        recur_ints = list(map(int, alarm[1]))
                        start_date = alarm[0].date() + timedelta(days=1)
                        x = alarm[0].time()
                        while start_date < alarm[2]:
                            if ((start_date.weekday() + 1) % 7) in recur_ints:
                                speak('removed alarm set for ' + self.datetime_to_string(alarm[0]))
                                self.alarms.remove(alarm)
                                self.alarms.append((datetime.combine(start_date, x), alarm[1], alarm[2]))
                                return
                            start_date += timedelta(days=1)
        
        speak('didnt get a valid time')

    def alarm_set(self, utr: str):
        """ Handles user utterance with intent 'alarm_remove' """

        # extract a recurring alarms expiration date if there is one
        recur = None
        until_data = None
        if any([ele in utr for ele in self.recurrences]):
            recur = set()
            for recuren in self.recurrence_dict:
                if recuren in utr:
                    for day in self.recurrence_dict[recuren].split():
                        recur.add(day)
            until_index = utr.rfind('until')
            if until_index == -1:
                until_data = utr[until_index:]
                utr = utr[:until_index]

        time_data = self.extract_datetime_en(utr)

        if not time_data:
            speak('Didnt get a valid time')
            return
        if time_data[0] <= datetime.now():
            speak('That time has already passed')
            return

        if recur:
            # processing for if a recurring alarm was detected
            until_date = None
            now = datetime.now()
            if until_data:
                until_date = self.extract_datetime_en(until_data)
            
            if not until_date:
                until_date = (now + timedelta(weeks=4)).date()
            else:
                until_date = until_date[0].date()
            
            x = time_data[0].time()
            curr_time = now.time()

            if curr_time < x:
                start_date = now.date()
            else:
                start_date = (now + timedelta(days=1)).date()
            
            recur_ints = list(map(int, recur))
            while start_date < until_date:
                if ((start_date.weekday() + 1) % 7) in recur_ints:
                    self.alarms.append((datetime.combine(start_date, x), recur, until_date))
                    break
                start_date += timedelta(days=1)
        else:
            self.alarms.append((time_data[0], None))

        self.alarms.sort(key=self.sort_func)
        with open('things/alarms.pkl', 'wb') as f:
            pickle.dump(self.alarms, f)

        speak('alarm set for ' + self.datetime_to_string(time_data[0], recur))

    def prune(self):
        """Keeps alarm list updated by removing old alarms and updating them if they are supposed to recur"""

        now = datetime.now()
        for alarm in self.alarms:
            if alarm[0] < now and not alarm[1]:
                self.alarms.remove(alarm)
            elif alarm[0] < now and alarm[1]:
                x = alarm[0].time()
                curr_time = now.time()

                if curr_time < x:
                    start_date = now.date()
                else:
                    start_date = (now + timedelta(days=1)).date()

                recur_ints = list(map(int, alarm[1]))
                while start_date < alarm[2]:
                    if ((start_date.weekday() + 1) % 7) in recur_ints:
                        self.alarms.remove(alarm)
                        self.alarms.append((datetime.combine(start_date, x), alarm[1], alarm[2]))
                        break
                    start_date += timedelta(days=1)
        
        self.alarms.sort(key=self.sort_func)
        with open('things/alarms.pkl', 'wb') as f:
            pickle.dump(self.alarms, f)

    def datetime_to_string(self, dt, recur=None):
        """ Returns a human readable string representation of a given datetime instance, now includes 
            funcionality for a recurring alarm as well"""

        time = datetime.now()
        
        if dt < time:
            return None
        
        time = time + timedelta(days=1)
        time = time.replace(hour=0, minute=0, second=0, microsecond=0)

        hours = dt.hour
        setting = "AM"
        if hours > 11:
            hours -= 12
            setting = "PM"
        if hours == 0:
            hours = 12
        time_data = num2words(hours) + (" " if 0 == dt.minute or dt.minute > 9 else " o ") + (num2words(dt.minute) + " " if dt.minute != 0 else "") + setting

        if recur:
            if recur == set('0123456'):
                recur_data = 'repeating daily'
            elif recur == set('12345'):
                recur_data = 'repeating each workday'
            elif recur == set('06'):
                recur_data = 'on weekends'
            else:
                recur_data = 'repeating every '
                rec_list = [x for x in recur]
                rec_list.sort()
                for i, item in enumerate(rec_list):
                    if len(recur) > 1 and i == len(recur) - 1:
                        recur_data += 'and ' + self.day_dict[item]
                    else:
                        recur_data += self.day_dict[item] + ', '
            return time_data + ' ' + recur_data           
        if dt < time:
            return time_data      
        time = time + timedelta(days=1)
        if dt < time:
            return "tomorrow at " + time_data
        time = time + timedelta(days=4)
        if dt < time:
            return dt.strftime("%A") + ' at ' + time_data
        else:
            return dt.strftime("%B ") + num2words(dt.day, to='ordinal') + " at " + time_data

    def extract_datetime_en(self, text, anchor_date=None, default_time=None):
        """Extracts a datetime from a string"""
        
        def clean_string(s):
            # normalize and lowercase utt  (replaces words with numbers)
            # clean unneeded punctuation and capitalization among other things.
            s = s.lower().replace('?', '').replace('.', '').replace(',', '') \
                .replace(' the ', ' ').replace(' a ', ' ').replace(' an ', ' ') \
                .replace("o' clock", "o'clock").replace("o clock", "o'clock") \
                .replace("o ' clock", "o'clock").replace("o 'clock", "o'clock") \
                .replace("oclock", "o'clock").replace("couple", "2") \
                .replace("centuries", "century").replace("decades", "decade") \
                .replace("millenniums", "millennium")

            wordList = s.split()
            for idx, word in enumerate(wordList):
                word = word.replace("'s", "")

                ordinals = ["rd", "st", "nd", "th"]
                if word[0].isdigit():
                    for ordinal in ordinals:
                        # "second" is the only case we should not do this
                        if ordinal in word and "second" not in word:
                            word = word.replace(ordinal, "")
                wordList[idx] = word

            return wordList

        def date_found():
            return found or \
                (
                    datestr != "" or
                    yearOffset != 0 or monthOffset != 0 or
                    dayOffset is True or hrOffset != 0 or
                    hrAbs or minOffset != 0 or
                    minAbs or secOffset != 0
                )

        if not anchor_date:
            anchor_date = datetime.now()

        if text == "":
            return None
        default_time = default_time or time(0, 0, 0)
        found = False
        daySpecified = False
        dayOffset = False
        monthOffset = 0
        yearOffset = 0
        today = anchor_date.strftime("%w")
        currentYear = anchor_date.strftime("%Y")
        fromFlag = False
        datestr = ""
        hasYear = False
        timeQualifier = ""

        timeQualifiersAM = ['morning']
        timeQualifiersPM = ['afternoon', 'evening', 'night', 'tonight']
        timeQualifiersList = set(timeQualifiersAM + timeQualifiersPM)
        year_markers = ['in', 'on', 'of']
        markers = year_markers + ['at', 'by', 'this', 'around', 'for', "within"]
        days = ['monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday', 'sunday']
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                'july', 'august', 'september', 'october', 'november',
                'december']
        recur_markers = days + [d + 's' for d in days] + ['weekend', 'weekday',
                                                        'weekends', 'weekdays']
        monthsShort = ['jan', 'feb', 'mar', 'apr', 'may', 'june', 'july', 'aug',
                    'sept', 'oct', 'nov', 'dec']
        year_multiples = ["decade", "century", "millennium"]
        day_multiples = ["weeks", "months", "years"]

        words = clean_string(text)

        for idx, word in enumerate(words):
            if word == "":
                continue
            wordPrevPrev = words[idx - 2] if idx > 1 else ""
            wordPrev = words[idx - 1] if idx > 0 else ""
            wordNext = words[idx + 1] if idx + 1 < len(words) else ""
            wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""

            # this isn't in clean string because I don't want to save back to words
            word = word.rstrip('s')
            start = idx
            used = 0
            # save timequalifier for later
            if word == "ago" and dayOffset:
                dayOffset = - dayOffset
                used += 1
            if word == "now" and not datestr:
                resultStr = " ".join(words[idx + 1:])
                resultStr = ' '.join(resultStr.split())
                extractedDate = anchor_date.replace(microsecond=0)
                return [extractedDate, resultStr]
            

            elif word in year_markers and is_numeric(wordNext) and len(wordNext) == 4:
                yearOffset = int(wordNext) - int(currentYear)
                used += 2
                hasYear = True
            # couple of
            elif word == "2" and wordNext == "of" and \
                    wordNextNext in year_multiples:
                multiplier = 2
                used += 3
                if wordNextNext == "decade":
                    yearOffset = multiplier * 10
                elif wordNextNext == "century":
                    yearOffset = multiplier * 100
                elif wordNextNext == "millennium":
                    yearOffset = multiplier * 1000
            elif word == "2" and wordNext == "of" and \
                    wordNextNext in day_multiples:
                multiplier = 2
                used += 3
                if wordNextNext == "years":
                    yearOffset = multiplier
                elif wordNextNext == "months":
                    monthOffset = multiplier
                elif wordNextNext == "weeks":
                    dayOffset = multiplier * 7
            elif word in timeQualifiersList:
                timeQualifier = word
            # parse today, tomorrow, day after tomorrow
            elif word == "today" and not fromFlag:
                dayOffset = 0
                used += 1
            elif word == "tomorrow" and not fromFlag:
                dayOffset = 1
                used += 1
            elif word == "day" and wordNext == "before" and wordNextNext == "yesterday" and not fromFlag:
                dayOffset = -2
                used += 3
            elif word == "before" and wordNext == "yesterday" and not fromFlag:
                dayOffset = -2
                used += 2
            elif word == "yesterday" and not fromFlag:
                dayOffset = -1
                used += 1
            elif (word == "day" and
                wordNext == "after" and
                wordNextNext == "tomorrow" and
                not fromFlag and
                (not wordPrev or not wordPrev[0].isdigit())):
                dayOffset = 2
                used = 3
                if wordPrev == "the":
                    start -= 1
                    used += 1
            # parse 5 days, 10 weeks, last week, next week
            elif word == "day":
                if wordPrev and wordPrev[0].isdigit():
                    dayOffset += int(wordPrev)
                    start -= 1
                    used = 2
            elif word == "week" and not fromFlag and wordPrev:
                if wordPrev[0].isdigit():
                    dayOffset += int(wordPrev) * 7
                    start -= 1
                    used = 2
                elif wordPrev == "next":
                    dayOffset = 7
                    start -= 1
                    used = 2
                elif wordPrev == "last":
                    dayOffset = -7
                    start -= 1
                    used = 2
            # parse 10 months, next month, last month
            elif word == "month" and not fromFlag and wordPrev:
                if wordPrev[0].isdigit():
                    monthOffset = int(wordPrev)
                    start -= 1
                    used = 2
                elif wordPrev == "next":
                    monthOffset = 1
                    start -= 1
                    used = 2
                elif wordPrev == "last":
                    monthOffset = -1
                    start -= 1
                    used = 2
            # parse 5 years, next year, last year
            elif word == "year" and not fromFlag and wordPrev:
                if wordPrev[0].isdigit():
                    yearOffset = int(wordPrev)
                    start -= 1
                    used = 2
                elif wordPrev == "next":
                    yearOffset = 1
                    start -= 1
                    used = 2
                elif wordPrev == "last":
                    yearOffset = -1
                    start -= 1
                    used = 2
            # parse Monday, Tuesday, etc., and next Monday,
            # last Tuesday, etc.
            elif word in days and not fromFlag:
                d = days.index(word)
                dayOffset = (d + 1) - int(today)
                used = 1
                if dayOffset < 0:
                    dayOffset += 7
                if wordPrev == "next":
                    if dayOffset <= 2:
                        dayOffset += 7
                    used += 1
                    start -= 1
                elif wordPrev == "last":
                    dayOffset -= 7
                    used += 1
                    start -= 1
            # parse 15 of July, June 20th, Feb 18, 19 of February
            elif word in months or word in monthsShort and not fromFlag:
                try:
                    m = months.index(word)
                except ValueError:
                    m = monthsShort.index(word)
                used += 1
                datestr = months[m]
                if wordPrev and (wordPrev[0].isdigit() or
                                (wordPrev == "of" and wordPrevPrev[0].isdigit())):
                    if wordPrev == "of" and wordPrevPrev[0].isdigit():
                        datestr += " " + words[idx - 2]
                        used += 1
                        start -= 1
                    else:
                        datestr += " " + wordPrev
                    start -= 1
                    used += 1
                    if wordNext and wordNext[0].isdigit():
                        datestr += " " + wordNext
                        used += 1
                        hasYear = True
                    else:
                        hasYear = False

                elif wordNext and wordNext[0].isdigit():
                    datestr += " " + wordNext
                    used += 1
                    if wordNextNext and wordNextNext[0].isdigit():
                        datestr += " " + wordNextNext
                        used += 1
                        hasYear = True
                    else:
                        hasYear = False

                # if no date indicators found, it may not be the month of May
                # may "i/we" ...
                # "... may be"
                elif word == 'may' and wordNext in ['i', 'we', 'be']:
                    datestr = ""

            # parse 5 days from tomorrow, 10 weeks from next thursday,
            # 2 months from July
            valid_followups = days + months + monthsShort
            valid_followups.append("today")
            valid_followups.append("tomorrow")
            valid_followups.append("yesterday")
            valid_followups.append("next")
            valid_followups.append("last")
            valid_followups.append("now")
            valid_followups.append("this")
            if (word == "from" or word == "after") and wordNext in valid_followups:
                used = 2
                fromFlag = True
                if wordNext == "tomorrow":
                    dayOffset += 1
                elif wordNext == "yesterday":
                    dayOffset -= 1
                elif wordNext in days:
                    d = days.index(wordNext)
                    tmpOffset = (d + 1) - int(today)
                    used = 2
                    if tmpOffset < 0:
                        tmpOffset += 7
                    dayOffset += tmpOffset
                elif wordNextNext and wordNextNext in days:
                    d = days.index(wordNextNext)
                    tmpOffset = (d + 1) - int(today)
                    used = 3
                    if wordNext == "next":
                        if dayOffset <= 2:
                            tmpOffset += 7
                        used += 1
                        start -= 1
                    elif wordNext == "last":
                        tmpOffset -= 7
                        used += 1
                        start -= 1
                    dayOffset += tmpOffset
            if used > 0:
                if start - 1 > 0 and words[start - 1] == "this":
                    start -= 1
                    used += 1

                for i in range(0, used):
                    words[i + start] = ""

                if start - 1 >= 0 and words[start - 1] in markers:
                    words[start - 1] = ""
                found = True
                daySpecified = True

        # parse time
        hrOffset = 0
        minOffset = 0
        secOffset = 0
        hrAbs = None
        minAbs = None
        military = False

        for idx, word in enumerate(words):
            if word == "":
                continue

            wordPrevPrev = words[idx - 2] if idx > 1 else ""
            wordPrev = words[idx - 1] if idx > 0 else ""
            wordNext = words[idx + 1] if idx + 1 < len(words) else ""
            wordNextNext = words[idx + 2] if idx + 2 < len(words) else ""
            # parse noon, midnight, morning, afternoon, evening
            used = 0
            if word == "noon":
                hrAbs = 12
                used += 1
            elif word == "midnight":
                hrAbs = 0
                used += 1
            elif word == "morning":
                if hrAbs is None:
                    hrAbs = 8
                used += 1
            elif word == "afternoon":
                if hrAbs is None:
                    hrAbs = 15
                used += 1
            elif word == "evening":
                if hrAbs is None:
                    hrAbs = 19
                used += 1
            elif word == "tonight" or word == "night":
                if hrAbs is None:
                    hrAbs = 22
                # used += 1 ## NOTE this breaks other tests, TODO refactor me!

            # couple of time_unit
            elif word == "2" and wordNext == "of" and \
                    wordNextNext in ["hours", "minutes", "seconds"]:
                used += 3
                if wordNextNext == "hours":
                    hrOffset = 2
                elif wordNextNext == "minutes":
                    minOffset = 2
                elif wordNextNext == "seconds":
                    secOffset = 2
            # parse half an hour, quarter hour
            elif word == "hour" and \
                    (wordPrev in markers or wordPrevPrev in markers):
                if wordPrev == "half":
                    minOffset = 30
                elif wordPrev == "quarter":
                    minOffset = 15
                elif wordPrevPrev == "quarter":
                    minOffset = 15
                    if idx > 2 and words[idx - 3] in markers:
                        words[idx - 3] = ""
                    words[idx - 2] = ""
                elif wordPrev == "within":
                    hrOffset = 1
                else:
                    hrOffset = 1
                if wordPrevPrev in markers:
                    words[idx - 2] = ""
                    if wordPrevPrev == "this":
                        daySpecified = True
                words[idx - 1] = ""
                used += 1
                hrAbs = -1
                minAbs = -1
                # parse 5:00 am, 12:00 p.m., etc
            # parse in a minute
            elif word == "minute" and wordPrev == "in":
                minOffset = 1
                words[idx - 1] = ""
                used += 1
            # parse in a second
            elif word == "second" and wordPrev == "in":
                secOffset = 1
                words[idx - 1] = ""
                used += 1
            elif word[0].isdigit():
                isTime = True
                strHH = ""
                strMM = ""
                remainder = ""
                wordNextNextNext = words[idx + 3] \
                    if idx + 3 < len(words) else ""
                if wordNext == "tonight" or wordNextNext == "tonight" or \
                        wordPrev == "tonight" or wordPrevPrev == "tonight" or \
                        wordNextNextNext == "tonight":
                    remainder = "pm"
                    used += 1
                    if wordPrev == "tonight":
                        words[idx - 1] = ""
                    if wordPrevPrev == "tonight":
                        words[idx - 2] = ""
                    if wordNextNext == "tonight":
                        used += 1
                    if wordNextNextNext == "tonight":
                        used += 1

                if ':' in word:
                    # parse colons
                    # "3:00 in the morning"
                    stage = 0
                    length = len(word)
                    for i in range(length):
                        if stage == 0:
                            if word[i].isdigit():
                                strHH += word[i]
                            elif word[i] == ":":
                                stage = 1
                            else:
                                stage = 2
                                i -= 1
                        elif stage == 1:
                            if word[i].isdigit():
                                strMM += word[i]
                            else:
                                stage = 2
                                i -= 1
                        elif stage == 2:
                            remainder = word[i:].replace(".", "")
                            break
                    if remainder == "":
                        nextWord = wordNext.replace(".", "")
                        if nextWord == "am" or nextWord == "pm":
                            remainder = nextWord
                            used += 1

                        elif wordNext == "in" and wordNextNext == "the" and \
                                words[idx + 3] == "morning":
                            remainder = "am"
                            used += 3
                        elif wordNext == "in" and wordNextNext == "the" and \
                                words[idx + 3] == "afternoon":
                            remainder = "pm"
                            used += 3
                        elif wordNext == "in" and wordNextNext == "the" and \
                                words[idx + 3] == "evening":
                            remainder = "pm"
                            used += 3
                        elif wordNext == "in" and wordNextNext == "morning":
                            remainder = "am"
                            used += 2
                        elif wordNext == "in" and wordNextNext == "afternoon":
                            remainder = "pm"
                            used += 2
                        elif wordNext == "in" and wordNextNext == "evening":
                            remainder = "pm"
                            used += 2
                        elif wordNext == "this" and wordNextNext == "morning":
                            remainder = "am"
                            used = 2
                            daySpecified = True
                        elif wordNext == "this" and wordNextNext == "afternoon":
                            remainder = "pm"
                            used = 2
                            daySpecified = True
                        elif wordNext == "this" and wordNextNext == "evening":
                            remainder = "pm"
                            used = 2
                            daySpecified = True
                        elif wordNext == "at" and wordNextNext == "night":
                            if strHH and int(strHH) > 5:
                                remainder = "pm"
                            else:
                                remainder = "am"
                            used += 2

                        else:
                            if timeQualifier != "":
                                military = True
                                if strHH and int(strHH) <= 12 and \
                                        (timeQualifier in timeQualifiersPM):
                                    strHH += str(int(strHH) + 12)

                else:
                    # try to parse numbers without colons
                    # 5 hours, 10 minutes etc.
                    length = len(word)
                    strNum = ""
                    remainder = ""
                    for i in range(length):
                        if word[i].isdigit():
                            strNum += word[i]
                        else:
                            remainder += word[i]

                    if remainder == "":
                        remainder = wordNext.replace(".", "").lstrip().rstrip()
                    if (
                            remainder == "pm" or
                            wordNext == "pm" or
                            remainder == "p.m." or
                            wordNext == "p.m."):
                        strHH = strNum
                        remainder = "pm"
                        used = 1
                    elif (
                            remainder == "am" or
                            wordNext == "am" or
                            remainder == "a.m." or
                            wordNext == "a.m."):
                        strHH = strNum
                        remainder = "am"
                        used = 1
                    elif (
                            remainder in recur_markers or
                            wordNext in recur_markers or
                            wordNextNext in recur_markers):
                        # Ex: "7 on mondays" or "3 this friday"
                        # Set strHH so that isTime == True
                        # when am or pm is not specified
                        strHH = strNum
                        used = 1
                    else:
                        if (
                                int(strNum) > 100 and
                                (
                                    wordPrev == "o" or
                                    wordPrev == "oh"
                                )):
                            # 0800 hours (pronounced oh-eight-hundred)
                            strHH = str(int(strNum) // 100)
                            strMM = str(int(strNum) % 100)
                            military = True
                            if wordNext == "hours":
                                used += 1
                        elif (
                                (wordNext == "hours" or wordNext == "hour" or
                                remainder == "hours" or remainder == "hour") and
                                word[0] != '0' and
                                (
                                    int(strNum) < 100 or
                                    int(strNum) > 2400
                                )):
                            # ignores military time
                            # "in 3 hours"
                            hrOffset = int(strNum)
                            used = 2
                            isTime = False
                            hrAbs = -1
                            minAbs = -1

                        elif wordNext == "minutes" or wordNext == "minute" or \
                                remainder == "minutes" or remainder == "minute":
                            # "in 10 minutes"
                            minOffset = int(strNum)
                            used = 2
                            isTime = False
                            hrAbs = -1
                            minAbs = -1
                        elif wordNext == "seconds" or wordNext == "second" \
                                or remainder == "seconds" or remainder == "second":
                            # in 5 seconds
                            secOffset = int(strNum)
                            used = 2
                            isTime = False
                            hrAbs = -1
                            minAbs = -1
                        elif int(strNum) > 100:
                            # military time, eg. "3300 hours"
                            strHH = str(int(strNum) // 100)
                            strMM = str(int(strNum) % 100)
                            military = True
                            if wordNext == "hours" or wordNext == "hour" or \
                                    remainder == "hours" or remainder == "hour":
                                used += 1
                        elif wordNext and wordNext[0].isdigit():
                            # military time, e.g. "04 38 hours"
                            strHH = strNum
                            strMM = wordNext
                            military = True
                            used += 1
                            if (wordNextNext == "hours" or
                                    wordNextNext == "hour" or
                                    remainder == "hours" or remainder == "hour"):
                                used += 1
                        elif (
                                wordNext == "" or wordNext == "o'clock" or
                                (
                                    wordNext == "in" and
                                    (
                                            wordNextNext == "the" or
                                            wordNextNext == timeQualifier
                                    )
                                ) or wordNext == 'tonight' or
                                wordNextNext == 'tonight'):

                            strHH = strNum
                            strMM = "00"
                            if wordNext == "o'clock":
                                used += 1

                            if wordNext == "in" or wordNextNext == "in":
                                used += (1 if wordNext == "in" else 2)
                                wordNextNextNext = words[idx + 3] \
                                    if idx + 3 < len(words) else ""

                                if (wordNextNext and
                                        (wordNextNext in timeQualifier or
                                        wordNextNextNext in timeQualifier)):
                                    if (wordNextNext in timeQualifiersPM or
                                            wordNextNextNext in timeQualifiersPM):
                                        remainder = "pm"
                                        used += 1
                                    if (wordNextNext in timeQualifiersAM or
                                            wordNextNextNext in timeQualifiersAM):
                                        remainder = "am"
                                        used += 1

                            if timeQualifier != "":
                                if timeQualifier in timeQualifiersPM:
                                    remainder = "pm"
                                    used += 1

                                elif timeQualifier in timeQualifiersAM:
                                    remainder = "am"
                                    used += 1
                                else:
                                    # TODO: Unsure if this is 100% accurate
                                    used += 1
                                    military = True
                        else:
                            isTime = False
                HH = int(strHH) if strHH else 0
                MM = int(strMM) if strMM else 0
                HH = HH + 12 if remainder == "pm" and HH < 12 else HH
                HH = HH - 12 if remainder == "am" and HH >= 12 else HH

                if (not military and
                        remainder not in ['am', 'pm', 'hours', 'minutes',
                                        "second", "seconds",
                                        "hour", "minute"] and
                        ((not daySpecified) or 0 <= dayOffset < 1)):

                    # ambiguous time, detect whether they mean this evening or
                    # the next morning based on whether it has already passed
                    if anchor_date.hour < HH or (anchor_date.hour == HH and
                                                anchor_date.minute < MM):
                        pass  # No modification needed
                    elif anchor_date.hour < HH + 12:
                        HH += 12
                    else:
                        # has passed, assume the next morning
                        dayOffset += 1

                if timeQualifier in timeQualifiersPM and HH < 12:
                    HH += 12

                if HH > 24 or MM > 59:
                    isTime = False
                    used = 0
                if isTime:
                    hrAbs = HH
                    minAbs = MM
                    used += 1

            if used > 0:
                # removed parsed words from the sentence
                for i in range(used):
                    if idx + i >= len(words):
                        break
                    words[idx + i] = ""

                if wordPrev == "o" or wordPrev == "oh":
                    words[words.index(wordPrev)] = ""

                if wordPrev == "early":
                    hrOffset = -1
                    words[idx - 1] = ""
                    idx -= 1
                elif wordPrev == "late":
                    hrOffset = 1
                    words[idx - 1] = ""
                    idx -= 1
                if idx > 0 and wordPrev in markers:
                    words[idx - 1] = ""
                    if wordPrev == "this":
                        daySpecified = True
                if idx > 1 and wordPrevPrev in markers:
                    words[idx - 2] = ""
                    if wordPrevPrev == "this":
                        daySpecified = True

                idx += used - 1
                found = True
        # check that we found a date
        if not date_found():
            return None

        if dayOffset is False:
            dayOffset = 0

        # perform date manipulation

        extractedDate = anchor_date.replace(microsecond=0)

        if datestr != "":
            # date included an explicit date, e.g. "june 5" or "june 2, 2017"
            try:
                temp = datetime.strptime(datestr, "%B %d")
            except ValueError:
                # Try again, allowing the year
                temp = datetime.strptime(datestr, "%B %d %Y")
            extractedDate = extractedDate.replace(hour=0, minute=0, second=0)
            if not hasYear:
                temp = temp.replace(year=extractedDate.year,
                                    tzinfo=extractedDate.tzinfo)
                if extractedDate < temp:
                    extractedDate = extractedDate.replace(
                        year=int(currentYear),
                        month=int(temp.strftime("%m")),
                        day=int(temp.strftime("%d")),
                        tzinfo=extractedDate.tzinfo)
                else:
                    extractedDate = extractedDate.replace(
                        year=int(currentYear) + 1,
                        month=int(temp.strftime("%m")),
                        day=int(temp.strftime("%d")),
                        tzinfo=extractedDate.tzinfo)
            else:
                extractedDate = extractedDate.replace(
                    year=int(temp.strftime("%Y")),
                    month=int(temp.strftime("%m")),
                    day=int(temp.strftime("%d")),
                    tzinfo=extractedDate.tzinfo)
        else:
            # ignore the current HH:MM:SS if relative using days or greater
            if hrOffset == 0 and minOffset == 0 and secOffset == 0:
                extractedDate = extractedDate.replace(hour=default_time.hour,
                                                    minute=default_time.minute,
                                                    second=default_time.second)

        if yearOffset != 0:
            extractedDate = extractedDate + relativedelta(years=yearOffset)
        if monthOffset != 0:
            extractedDate = extractedDate + relativedelta(months=monthOffset)
        if dayOffset != 0:
            extractedDate = extractedDate + relativedelta(days=dayOffset)
        if hrOffset != 0:
            extractedDate = extractedDate + relativedelta(hours=hrOffset)
        if minOffset != 0:
            extractedDate = extractedDate + relativedelta(minutes=minOffset)
        if secOffset != 0:
            extractedDate = extractedDate + relativedelta(seconds=secOffset)

        if hrAbs != -1 and minAbs != -1 and not hrOffset and not minOffset and not secOffset:
            # If no time was supplied in the string set the time to default
            # time if it's available
            if hrAbs is None and minAbs is None and default_time is not None:
                hrAbs, minAbs = default_time.hour, default_time.minute
            else:
                hrAbs = hrAbs or 0
                minAbs = minAbs or 0

            extractedDate = extractedDate.replace(hour=hrAbs,
                                                minute=minAbs)

            if (hrAbs != 0 or minAbs != 0) and datestr == "":
                if not daySpecified and anchor_date > extractedDate:
                    extractedDate = extractedDate + relativedelta(days=1)

        for idx, word in enumerate(words):
            if words[idx] == "and" and \
                    words[idx - 1] == "" and words[idx + 1] == "":
                words[idx] = ""

        resultStr = " ".join(words)
        resultStr = ' '.join(resultStr.split())
        return [extractedDate, resultStr]
