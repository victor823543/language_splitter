import whisper
import os
import ssl
from easygoogletranslate import EasyGoogleTranslate as translate
import requests
from pydub import AudioSegment
from rapidfuzz import fuzz
import pickle

ssl._create_default_https_context = ssl._create_unverified_context

translator = translate(source_language='es', target_language='en', timeout=10)

#Classes
class Sentence:
    def __init__(self, id):
        self.id = id
        self.completed = False
        self.words = []
        self.length = 0
        self.similarity = 0

    def addWord(self, word):
        new_word = word
        self.words.append(new_word)
        self.length += 1

    def removeWord(self, id):
        if 0 <= id < len(self.words):
            del self.words[id]
            self.length -= 1
    
    def removeLatest(self, times):
        for _ in range(times):
            self.removeWord(len(self.words) - 1)
    
    def storeSelf(self, prep_class):
        prep_class.addSentence(self)

    def retrieveAsString(self):
        string = ''.join([word['word'] for word in self.words])
        return string
    
    def combineSentence(self, other, prep_class):
        for word in other.words:
            self.words.append(word)
            self.length += 1
        prep_class.sentences.remove(other)

class Preparation:
    def __init__(self):
        self.sentences = []
        self.similarity_whole = 0
    
    def addSentence(self, sentence):
        self.sentences.append(sentence)
    
    def calculateSimilarity(self):
        tot_similarity = 0.0
        for sentence in self.sentences:
            tot_similarity += sentence.similarity
        self.similarity_whole = tot_similarity 

    def getLatestId(self):
        return self.sentences[-1].id
    
    def getLength(self):
        return len(self.sentences)
    
    def getTimeStampList(self):
        list = []
        for sentence in self.sentences:
            ending = float(sentence.words[-1]['end'])
            list.append(ending)
        return list
#_______________



#Check similarity function
def check_similarity(sentencesA, sentencesB):

    text_a = ''.join([x.retrieveAsString() for x in sentencesA])
    text_b = ''.join([x.retrieveAsString() for x in sentencesB])
    text_b = translator.translate(text_b)
    n = fuzz.ratio(text_a, text_b)
    n = n/100
    return n
#____________

#Mixing files functions
def fileSlicing(file, timestamps):
    sentences = []
    
    for timestamp in timestamps:
        timestamp_id = timestamps.index(timestamp)
        if timestamp_id + 1 < len(timestamps):
            next_timestamp = timestamps[timestamp_id + 1]
            sentence = file[timestamp:next_timestamp]
            sentences.append(sentence)
        else: 
            break
       
    return sentences


def sentenceCombining(sentencesA, sentencesB):
    combined_file = sentencesA[0] + sentencesB[0]
    for index, sentenceA in enumerate(sentencesA):
        if index == 0:
            continue
        else:
            try:
                combined_sound = sentenceA + sentencesB[index]
                combined_file = combined_file + combined_sound
            except IndexError:
                break
    return combined_file

def mixFiles(file_a, file_b, timestamps_a, timestamps_b, name):
    sentences_a = fileSlicing(file_a, timestamps_a)
    sentences_b = fileSlicing(file_b, timestamps_b)

    new_file = sentenceCombining(sentences_a, sentences_b)
    folder = os.path.abspath("Audio/MixedAudio")
    #folder = os.path.abspath("language_app/static/language_app/audio")
    output = f"{folder}/{name}"
    new_file.export(output, format="mp3")
#______________________

#Functions for transcribing files || returns result['segments']
#If store=True, stores object as pkl object
def transcribe(filename, store=False, pkl_name=None):
    filename = f'Audio/ShortenedAudio/{filename}.mp3'
    path = os.path.abspath(filename)
    #Change model for more accuracy or more efficiency
    model = whisper.load_model("base")
    result = model.transcribe(path, word_timestamps=True)
    segments = result['segments']

    #Store as pkl object (appropriate for faster debugging)
    if store and pkl_name:
        with open(pkl_name, 'wb') as file:
            pickle.dump(result, file)
    
    return segments

#If using existing pkl file (for debugging)
def get_pkl(pkl_name):
    with open(pkl_name, 'rb') as file:
        result = pickle.load(file)
    
    segments = result['segments']
    return segments
#____________________________

#Functions for creating accurate segments per sentence || Returns setOfSentences class object
def create_sentences(segments):

    #Creating classes
    setOfSentences = Preparation()
    sentence = Sentence(1)

    #Creating new and accurate segments per sentences
    for segment in segments:
        for index, word in enumerate(segment['words']):
            if '.' in word['word'] or '?' in word['word'] or '!' in word['word']:
                if (index+1 == len(segment['words']) or float(segment['words'][index + 1]['start']) - float(word['end']) > 0.10) and (sentence.length > 2):
                    sentence.addWord(word)
                    sentence.completed = True
                    sentence.storeSelf(setOfSentences)
                    latest_id = setOfSentences.getLatestId()
                    sentence = Sentence(int(latest_id) + 1)   
                else:
                    sentence.addWord(word)        
            else:
                sentence.addWord(word)
    
    return setOfSentences
#___________________________

#Functions for alignment

#Function for double checking || if True: returns max similarity value, if False: returns False
def double_check(setOfSentences_A, setOfSentences_B, index_en, index_es):
    #Function for checking whether a choice was correct by the performance by the following sentence
    dc_similarities = []
    #Creating variables
    try:
        sentence_en = setOfSentences_A.sentences[index_en]
        sentence_es = setOfSentences_B.sentences[index_es]

        #Checking the normal (1-1)
        dc_similarity = check_similarity([sentence_en], [sentence_es])
        dc_similarities.append(dc_similarity)

    except IndexError:
        return False
    try:
        sentence_en_2 = setOfSentences_A.sentences[index_en + 1]

        #Checking test 2 (2-1)
        dc_similarity_3 = check_similarity([sentence_en, sentence_en_2], [sentence_es])
        dc_similarities.append(dc_similarity_3)

    except IndexError:
        pass
    try:
        sentence_es_2 = setOfSentences_B.sentences[index_es + 1]

        #Checking test 1 (1-2)
        dc_similarity_2 = check_similarity([sentence_en], [sentence_es, sentence_es_2])
        dc_similarities.append(dc_similarity_2)
        
    except IndexError:
        pass
    try:
        sentence_en_3 = setOfSentences_A.sentences[index_en + 2]

        #Checking test 4 (3-1)
        dc_similarity_5 = check_similarity([sentence_en, sentence_en_2, sentence_en_3], [sentence_es])
        dc_similarities.append(dc_similarity_5)

    except IndexError:
        pass
    try:
        sentence_es_3 = setOfSentences_B.sentences[index_es + 2]

        #Checking test 3 (1-3)
        dc_similarity_4 = check_similarity([sentence_en], [sentence_es, sentence_es_2, sentence_es_3])
        dc_similarities.append(dc_similarity_4)

    except IndexError:
        pass

    #Getting max value
    if dc_similarities:
        max_value = max(dc_similarities)
        return max_value
    else:
        return False
    #_ _ _ _ _ _ _ _ _ _ _ _ _ 

#Main function for alignment || returns timestamps
def align(setOfSentences_en, setOfSentences_es):
    for index, sentence in enumerate(setOfSentences_en.sentences):
        
        try:
            
            sentence_es = setOfSentences_es.sentences[index]
            new_index = index
            similarity = check_similarity([sentence], [sentence_es])
            if similarity < 0.7:
                #Test different possibilities
                #List of the results form similarity check from each posibility
                similarity_comparison = [similarity]
                
                
                #First test (1-2)
                try:
                    sentence_es_2 = setOfSentences_es.sentences[new_index + 1]
                except IndexError:
                    continue
                first_similarity = check_similarity([sentence], [sentence_es, sentence_es_2])
                similarity_comparison.append(first_similarity)
                if first_similarity > similarity + 0.1 and first_similarity > 0.8:
                    setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                    continue
                else:
                    #Second test (2-1)
                    try:
                        sentence_en_2 = setOfSentences_en.sentences[index + 1]
                    except IndexError:
                        continue
                    second_similarity = check_similarity([sentence, sentence_en_2], [sentence_es])
                    similarity_comparison.append(second_similarity)
                    if first_similarity + 0.1 < second_similarity > similarity + 0.1 and second_similarity > 0.8:
                        sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                        continue
                    else:
                        #Third test (1-3)
                        try:
                            sentence_es_3 = setOfSentences_es.sentences[new_index + 2] 
                            third_similarity = check_similarity([sentence], [sentence_es, sentence_es_2, sentence_es_3])
                            similarity_comparison.append(third_similarity)
                            if third_similarity > max(similarity_comparison) and third_similarity > 0.8:
                                setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                                setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                                continue
                        except IndexError:
                            pass
                        else:
                            #Fourth test (3-1)
                            try:
                                sentence_en_3 = setOfSentences_en.sentences[index + 2]                                 
                                fourth_similarity = check_similarity([sentence, sentence_en_2, sentence_en_3], [sentence_es])
                                similarity_comparison.append(fourth_similarity)
                                if fourth_similarity > max(similarity_comparison) and fourth_similarity > 0.8:
                                    sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                                    sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                                    continue
                            except IndexError:
                                pass
            
                
                #Checking which test performed the best and choosing actions accordingly
                #Creating list of indexes in similarity_comparison with the three max values in declining order
                max_index_list = []
                max_values_list = []
                for _ in range(3):
                    max_similarity_index, max_similarity = max(enumerate(similarity_comparison), key=lambda x: x[1])
                    max_index_list.append(max_similarity_index)
                    max_values_list.append(max_similarity)
                    similarity_comparison[max_similarity_index] = 0.0
                
                finished = False
                goal_similarity = 0.7
                combined_results = {}
                for _ in range(2):
                    for m_index in max_index_list:
                        if m_index == 0:
                            result_check = double_check(setOfSentences_en, setOfSentences_es, index + 1, new_index + 1)
                            combined_results[0] = result_check + max_values_list[max_index_list.index(0)]
                        if (m_index == 0) and (not result_check or result_check > goal_similarity):
                            finished = True
                            break  
                        if m_index == 1:
                            result_check = double_check(setOfSentences_en, setOfSentences_es, index + 1, new_index + 2)
                            combined_results[1] = result_check + max_values_list[max_index_list.index(1)]
                        if (m_index == 1) and (not result_check or result_check > goal_similarity):
                            setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                            finished = True
                            break
                        if m_index == 2:
                            result_check = double_check(setOfSentences_en, setOfSentences_es, index + 2, new_index + 1)
                            combined_results[2] = result_check + max_values_list[max_index_list.index(2)]
                        if (m_index == 2) and (not result_check or result_check > goal_similarity):
                            sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                            finished = True
                            break
                        if m_index == 3:
                            result_check = double_check(setOfSentences_en, setOfSentences_es, index + 1, new_index + 3)
                            combined_results[3] = result_check + max_values_list[max_index_list.index(3)]
                        if (m_index == 3) and (not result_check or result_check > goal_similarity):
                            setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                            setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                            finished = True
                            break
                        if m_index == 4:
                            result_check = double_check(setOfSentences_en, setOfSentences_es, index + 3, new_index + 1)
                            combined_results[4] = result_check + max_values_list[max_index_list.index(4)]
                        if (m_index == 4) and (not result_check or result_check > goal_similarity):
                            sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                            sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                            finished = True
                            break
                    goal_similarity -= 0.1
                    if finished:
                        break
                if not finished:
                    last_resort_index = max(combined_results, key=lambda k: combined_results[k])
                    if last_resort_index == 1:
                        setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                    elif last_resort_index == 2:
                        sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                    elif last_resort_index == 3:
                        setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                        setOfSentences_es.sentences[new_index].combineSentence(setOfSentences_es.sentences[new_index + 1], setOfSentences_es)
                    elif last_resort_index == 4:
                        sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)
                        sentence.combineSentence(setOfSentences_en.sentences[index + 1], setOfSentences_en)

                        
                    
            print(sentence.retrieveAsString())
            print(setOfSentences_es.sentences[new_index].retrieveAsString())
        except IndexError:
            print('index error')
            break
    
    #Creating lists of timestamps
    timestamps_en = setOfSentences_en.getTimeStampList()
    timestamps_en = [x*1000 for x in timestamps_en]
    timestamps_en.insert(0, 0.0)
    timestamps_es = setOfSentences_es.getTimeStampList()
    timestamps_es = [x*1000 for x in timestamps_es]
    timestamps_es.insert(0, 0.0)

    return timestamps_en, timestamps_es
#_ _ _ _ _ _ _ _ _ _ _ _ _ _

#______________________________________

#Main function -- parameters (Name of file to export, name of first language file, name of second language file,
# pickle options [0=transcribe, 1=get from pickle obj, 2=transcribe and store], name of first pickle file, name of second pickle file)
def split_audio(filename_out, filename1=None, filename2=None, pkl=0, pkl_name_A=None, pkl_name_B=None):

    #Transcribing audiofiles
    if not pkl:
        segments_en = transcribe(filename1)
        segments_es = transcribe(filename2)
    if pkl == 1:
        segments_en = get_pkl(pkl_name_A)
        segments_es = get_pkl(pkl_name_B)
    if pkl == 2:
        segments_en = transcribe(filename1, True, pkl_name_A)
        segments_es = transcribe(filename2, True, pkl_name_B)

    #Creating classes
    #First language
    setOfSentences_en = create_sentences(segments_en)

    #Creating classes
    #Second language
    setOfSentences_es = create_sentences(segments_es)

    #Aligning sentences
    timestamps_en, timestamps_es = align(setOfSentences_en, setOfSentences_es)

    #Calling the filemixing function
    filename_en = f'Audio/ShortenedAudio/{filename1}.mp3'
    path_eng = os.path.abspath(filename_en)
    filename_es = f'Audio/ShortenedAudio/{filename2}.mp3'
    path_esp = os.path.abspath(filename_es)
    file_en = AudioSegment.from_mp3(path_eng)
    file_es = AudioSegment.from_mp3(path_esp)
    file_out = f'{filename_out}.mp3'
    mixFiles(file_en, file_es, timestamps_en, timestamps_es, file_out)


    


split_audio('sherlock_mixed_1', 'english_original_a', 'spanish_original_a', 2, 'PickleObjects/english_obj.pkl', 'PickleObjects/spanish_obj.pkl')



