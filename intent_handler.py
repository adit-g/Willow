
from utils.padaos import IntentContainer
from skills.spelling import SpellingSkill
from skills.timer import AlarmSkill

class IntentHandler:
    """Willow's intent handler, contains methods that properly responds to 
    user utterance based on the intent behind it"""

    def __init__(self):
        # this container holds all special intents that the NLP model wasn't trained on
        self.container = IntentContainer()

        # special intents
        # each special skill must have methods to add their sub-intents to container defined above
        spelling = SpellingSkill()
        self.special_skills = {'spelling' : spelling}

        # regular skills
        alarm = AlarmSkill()
        self.reg_skills = {'alarm': alarm}

        # adds all sub-intents from each special skill to a 
        # mega-container with all special skills
        for skill in self.special_skills.values():
            skill.add_intents(self.container)
    
    def handle_special_intents(self, utr):
        """ If special intent is found in user utterance, this method handles it accordingly
            else, it returns False """

        data = self.container.calc_intent(utr)
        name = data['name']
        if name == None:
            return (False, '')
        
        response = self.special_skills[name.split('_')[0]].handle_intent(data)
        return (True, response)
    
    def handle_regular_intent(self, utr, intent_index):
        """Handles intents that the model has been trained on"""
    
        if intent_index == 0:
            self.reg_skills['alarm'].alarm_query(utr)
        elif intent_index == 1:
            self.reg_skills['alarm'].alarm_remove(utr)
        elif intent_index == 2:
            self.reg_skills['alarm'].alarm_set(utr)
    
    def check_for_alarm(self):
        """returns true if an alarm is going off rn"""
        bru = self.reg_skills['alarm'].check_for_alarm()

        if bru:
            self.reg_skills['alarm'].prune()
            return True
        
        return False