
class SpellingSkill:
    """Willow's official spelling skill"""

    def add_intents(self, container):
        container.add_intent('spelling_spell_word', [
            'spell (word|the word|) {word}', 'spelling (of|for|) (the word|word|) {word}',
            'spell out (the word|word|) {word}', '(the word|word|) {word} is spelled how',
            'how is (the word|word|) {word} spelled', 'how (the word|word|) {word} is spelled', '{word} spelling'
        ])
        container.add_intent('spelling_count_letters', [
            'how many {letter} (can you find|are|) in (word|the word) {word}', 
        ])
        return container

    def handle_intent(self, data):
        if data['name'] == 'spelling_spell_word':
            word = data['entities']['word']
            spelled_word = '; '.join(word).upper() + ';'
            return word + " is spelled " + spelled_word
        elif data['name'] == 'spelling_count_letters':
            letter = data['entities']['letter'][0]
            word = data['entities']['word']
            return "the letter " + letter.upper() + " appears " + str(word.count(letter)) + " times in the word " + word
        return ''
        
