from audio import transcribe, get_pkl, mixFiles
from text import split_text
from rapidfuzz import fuzz
import json, re, copy

class AlignmentError(Exception):
    pass

def count_words(string):
    words = string.split()
    return len(words)

def cleanse_string(string):
    cleansed_string = re.sub(r'[^a-z0-9áéíóúñüàèêçœæäöß]', '', string.lower())
    return cleansed_string

def text_similarity_check(segment, text):
    diff = abs(len(segment.split()) - len(text.split()))
    length_comparison_points = 10 - (diff * 3)

    string_similarity = fuzz.ratio(cleanse_string(segment), cleanse_string(text))
    n = string_similarity + length_comparison_points
    n = n/100
    return n

def word_similarity_check(word1, word2):
    word_similarity = fuzz.ratio(word1, word2)
    n = word_similarity / 100
    return n

def margin_calculation(n):
    if n >= 15:
        return n/20 + 4
    else:
        return 3.1

def get_string_from_sentence(sentence):
    string = ''.join([word['word'] for word in sentence])
    return string

def get_timestamps(sentences):
    timestamps = []
    for sentence in sentences:
        ending = float(sentence[-1]['end'])
        timestamps.append(ending + 0.3)
    return timestamps

def prepare_timestamps_for_audio_mixing(timestamps):
    modified_timestamps = [x*1000 for x in timestamps]
    modified_timestamps.insert(0, 0.0)
    return modified_timestamps

def combine_segments(segments):
    words = []
    for segment in segments:
        for word in segment['words']:
            words.append(word)
    return words


def update_text_info(index, text_list):
    text = text_list[index]
    text_words = text.split()
    text_word = cleanse_string(text_words[-1])
    text_length = len(text_words)
    margin = margin_calculation(text_length)
    return text, text_word, text_length, margin

def check_end_word_alignment(audio_word, text_word, text_length, margin, word_number, all_words, word_index, text_list, text_index, sentence):
    #for debugging
    try:
        if text_word == 'warsawyes':
            print('debug')
        if text_word == 'esq':
            print('debug')
    #__________

        print(f'Audio: {audio_word} \n Text: {text_word}')
        is_false_probability = 0
        is_certainly_false = 0
        is_true_probability = 0
        is_certainly_true = 0
        original_word = all_words[word_index]
        original_word_index = word_index
        this_text = text_list[text_index]
        audio_sentence = get_string_from_sentence(sentence)
        sentence_similarity = text_similarity_check(audio_sentence, this_text)
        if audio_word == text_word and sentence_similarity > 0.9:
            return True
        else:
            similarity = word_similarity_check(audio_word, text_word)
            print(f'Similarity: {similarity}')
            if similarity > 0.8 and sentence_similarity > 0.9:
                return True
            else:
                new_word_number = word_number + 1
                all_sentence_similarities = [sentence_similarity]
                other_words_uncleansed = []
                other_words = []

                add_true_probability = True
                have_added_to_false = False
                while new_word_number <= text_length + margin + 1:
                    word_index += 1
                    word = all_words[word_index]
                    other_words_uncleansed.append(word['word'])
                    audio_word = cleanse_string(word['word'])
                    other_words.append(audio_word)
                    new_sentence_addition = ' '.join([word_addition for word_addition in other_words])
                    new_audio_sentence = f'{audio_sentence} {new_sentence_addition}'
                    new_sentence_similarity = text_similarity_check(new_audio_sentence, this_text)
                    all_sentence_similarities.append(new_sentence_similarity)

                    if audio_word == text_word:
                        is_false_probability += 1
                        is_certainly_false += 1
                        if new_sentence_similarity > sentence_similarity:
                            return False
                    else:
                        new_similarity = word_similarity_check(audio_word, text_word)
                        
                        if new_similarity > similarity:
                            if not have_added_to_false:
                                is_false_probability += 1
                                have_added_to_false = True
                                add_true_probability = False
                            if new_sentence_similarity > sentence_similarity and new_similarity > 0.6:
                                return False

                    new_word_number += 1
                if add_true_probability:
                    is_true_probability += 1

                if similarity > 0.5 and sentence_similarity > 0.9: 
                    is_true_probability += 1
                else:
                    is_false_probability += 1
                if all_sentence_similarities:
                    if sentence_similarity == max(all_sentence_similarities):
                        is_true_probability += 1
                    elif sentence_similarity < max(all_sentence_similarities) - 0.15:
                        is_false_probability += 1
                else: 
                    is_true_probability += 1
                    

                add_true_probability2 = True
                for punctuation in ['.', '!', '?']:
                    if punctuation in original_word['word']:
                        is_true_probability += 1
                        is_certainly_true += 1
                    similarity_check_additions = []
                    for other_word_index, other_word in enumerate(other_words_uncleansed):
                        clean_other_word = other_words[other_word_index]
                        similarity_check_additions.append(clean_other_word)
                        new_sentence_addition = ' '.join([word_addition for word_addition in similarity_check_additions])
                        new_audio_sentence = f'{audio_sentence} {new_sentence_addition}'
                        new_sentence_similarity = text_similarity_check(new_audio_sentence, this_text)
                        if punctuation in other_word:
                            is_false_probability += 1
                            is_certainly_false += 1
                            add_true_probability2 = False
                            if new_sentence_similarity > sentence_similarity:
                                return False
                if add_true_probability2:
                    is_true_probability += 1
                next_text = text_list[text_index + 1].split()
                first_word = cleanse_string(next_text[0])
                for other_word_index, other_word in enumerate(other_words):
                    if other_word_index == 0 and sentence_similarity > 0.8:
                        if other_word == first_word:
                            is_true_probability += 1
                            is_certainly_true += 1
                        else:
                            other_word_similarity = word_similarity_check(other_word, first_word)
                            if other_word_similarity > 0.7 and sentence_similarity > 0.8:
                                is_true_probability += 1
                                is_certainly_true += 1
                    else:
                        if other_word == first_word:
                            is_false_probability += 1
                            is_certainly_false += 1
                        else:
                            other_word_similarity = word_similarity_check(other_word, first_word)
                            if other_word_similarity > 0.7:
                                is_false_probability += 1
                if is_certainly_false >= 2:
                    return False
                if is_certainly_true >= 2:
                    return True
                if is_false_probability > is_true_probability:
                    return False
                else:
                    return True
    except IndexError:
        if original_word_index == len(all_words) - 1:
            return True
        else: 
            return False
            

def create_sentences_with_text(segments, text_list, parts, part):
    if parts and part:
        text_start_index = parts[part - 1]
        sliced_text_list = text_list[text_start_index:]
    words = combine_segments(segments)
    sentences = []
    sentence = []
    
    text = text_word = text_length = margin = None

    for word_index, word in enumerate(words):
        index = len(sentences)
        if not sentence:
            text, text_word, text_length, margin = update_text_info(index, sliced_text_list)
        audio_word = cleanse_string(word['word'])
        word_number = len(sentence) + 1
        sentence.append(word)

        if text_length - margin < word_number < text_length + margin:
            status = check_end_word_alignment(audio_word, text_word, text_length, margin, word_number, words, word_index, sliced_text_list, index, sentence)

            if status:
                sentences.append(copy.deepcopy(sentence))
                print('ACCEPTED')
                print(f'Audio whole: \n {get_string_from_sentence(sentence)}')
                print(f'Text whole: \n {text}')
                sentence = []
            else:
                print('NOT ACCEPTED')

    return sentences

def split_audio_with_text(filename_out, filename1, filename2, pkl_option, text_option, pkl_object1=None, pkl_object2=None, json_object=None, text_files=None, output_json=None, part=None):
    '''
    pkl_option 0:
        Create audio object from scratch. Neither use existing object nor store into pickle file.

    pkl_option 1:
        Create audio object from scratch, store in a pickle file for eventual later use. pkl_object 1 and 2 
        must be the relative path including name of output file. Must end with .pkl

    pkl_option 2:
        Use already existing audio object from a pkl-file. pkl_object 1 and 2 must be the relative path to the objects.

    text_option 0: 
        Create new text object from scratch from two .txt files. json_object must be None (as per default) and 
        text_files must be a list of the relative paths to the two .txt files.

    text_option 1:
        Load text object from json_file by providing the relative path as an argument to json_object
        or by giving the function a json object directly as an argument to json_object

    text_option 2:
        Provide the function with a python object (dictionary) as an argument to json_object
    '''

    if not pkl_option:
        segments_a = transcribe(filename1)
        segments_b = transcribe(filename2)
    if pkl_option == 1:
        segments_a = transcribe(filename1, True, pkl_object1)
        segments_b = transcribe(filename2, True, pkl_object2)
    if pkl_option == 2:
        segments_a = get_pkl(pkl_object1)
        segments_b = get_pkl(pkl_object2)
    
    if not text_option:
        text_object = split_text(text_files[0], text_files[1], 0)
    if text_option == 1:
        try:
            text_object = json.loads(json_object)
        except json.JSONDecodeError:
            if isinstance(json_object, str):
                with open(json_object, 'r') as file:
                    text_object = json.load(file)
            else:
                print('Error: Wrongful input for json_object')
    if text_option == 2:
        if isinstance(json_object, dict):
            text_object = json_object
        else:
            print('Error: Not a python object')
    
    sentences_a = create_sentences_with_text(segments_a, text_object['text_a'], text_object['parts'] if text_object['parts'] else None, part) 
    sentences_b = create_sentences_with_text(segments_b, text_object['text_b'], text_object['parts'] if text_object['parts'] else None, part)     

    timestamps_a = get_timestamps(sentences_a)
    timestamps_b = get_timestamps(sentences_b)

    modified_stamps_a = prepare_timestamps_for_audio_mixing(timestamps_a)
    modified_stamps_b = prepare_timestamps_for_audio_mixing(timestamps_b)

    text_object['timestamps'] = {'timestamps_a': timestamps_a, 'timestamps_b': timestamps_b}
    full_json_object = json.dumps(text_object)
    if output_json:
        with open(output_json, 'w') as file:
            file.write(full_json_object)

    mixFiles(filename1, filename2, modified_stamps_a, modified_stamps_b, filename_out)


