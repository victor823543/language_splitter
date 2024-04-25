from easygoogletranslate import EasyGoogleTranslate as translate
from rapidfuzz import fuzz
import re
import json
import spacy

LLM_ES = 'es_core_news_sm'
LLM_EN = 'en_core_web_sm'

translator = translate(source_language='es', target_language='en', timeout=30)

def read_sentences_from_file(file_path, language):
    if language == 'en':
        model = LLM_EN
    if language == 'es':
        model = LLM_ES

    nlp = spacy.load(model)
    sentences = []
    with open(file_path, 'r') as file:
        # Read the entire content of the file
        content = file.read()

        # Remove potentially disturbing characters
        content = content.replace("'", "").replace('"', '').replace('”', '').replace('“', '').replace('...', '')

        # Remove newline characters
        content = content.replace('\n', ' ')

        '''
        OLD SPLITTING
        # Split the content into sentences using regular expressions
        pattern = r'(?<!Mr|Ms|Mrs)[.!?]\s+'
        sentences = re.split(pattern, content)
        '''

        doc = nlp(content)
        sentences = [sentence.text for sentence in doc.sents]
   
    # Remove empty sentences
    sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    
    return sentences

def check_similarity(sentences_a, sentences_b):

    text_a = ''.join([x for x in sentences_a])
    text_b = ''.join([x for x in sentences_b])
    length_a = len(text_a.split())
    length_b = len(text_b.split())

    diff = abs(length_a - length_b)
    length_comparison_points = 10 - (diff * 3)

    text_b = translator.translate(text_b)
    n = fuzz.ratio(text_a, text_b)
    n = n + length_comparison_points
    n = n/100
    return n

def combine_sentences(target_sentence, number_of_additions, target_list, current_index, aligned_list, other_sentence, other_list):
    addition = ' '.join([target_list.pop(current_index + 1) for _ in range(number_of_additions)])
    target_sentence = target_sentence + ' ' + addition
    aligned_list.append(target_sentence)
    other_list.append(other_sentence)

#Function for double checking || if True: returns max similarity value, if False: returns False
def double_check(sentences_a, sentences_b, index_a, index_b):
    #Function for checking whether a choice was correct by the performance by the following sentence
    dc_similarities = []
    #Creating variables
    try:
        sentence_en = sentences_a[index_a]
        sentence_es = sentences_b[index_b]

        #Checking the normal (1-1)
        dc_similarity = check_similarity([sentence_en], [sentence_es])
        dc_similarities.append(dc_similarity)

    except IndexError:
        return False
    
    try:
        sentence_en_2 = sentences_a[index_a + 1]

        #Checking test 2 (2-1)
        dc_similarity_3 = check_similarity([sentence_en, sentence_en_2], [sentence_es])
        dc_similarities.append(dc_similarity_3)

    except IndexError:
        pass
    try:
        sentence_es_2 = sentences_b[index_b + 1]

        #Checking test 1 (1-2)
        dc_similarity_2 = check_similarity([sentence_en], [sentence_es, sentence_es_2])
        dc_similarities.append(dc_similarity_2)
        
    except IndexError:
        pass
    try:
        sentence_en_3 = sentences_a[index_a + 2]

        #Checking test 4 (3-1)
        dc_similarity_5 = check_similarity([sentence_en, sentence_en_2, sentence_en_3], [sentence_es])
        dc_similarities.append(dc_similarity_5)

    except IndexError:
        pass
    try:
        sentence_es_3 = sentences_b[index_b + 2]

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

def align_text(sentences_a, sentences_b, aligned_sentences_a, aligned_sentences_b, similarities, warnings):
    
    run = True
    for index in range(len(sentences_a)):
        
        while run:
            try:    
                sentence_a = sentences_a[index]
                sentence_b = sentences_b[index]
                
                similarity = check_similarity([sentence_a], [sentence_b])
                if similarity < 0.75:
                    #Test different possibilities
                    #List of the results form similarity check from each posibility
                    similarity_comparison = [similarity]
                    
                    
                    #First test (1-2)
                    try:
                        sentence_b_2 = sentences_b[index + 1]
                        first_similarity = check_similarity([sentence_a], [sentence_b, sentence_b_2])
                        similarity_comparison.append(first_similarity)
                        if first_similarity > similarity + 0.1 and first_similarity > 0.8:
                            combine_sentences(sentence_b, 1, sentences_b, index, aligned_sentences_b, sentence_a, aligned_sentences_a)
                            final_similarity = first_similarity
                            break
                    except IndexError:
                        pass
                    #Second test (2-1)
                    try:
                        sentence_a_2 = sentences_a[index + 1]
                        second_similarity = check_similarity([sentence_a, sentence_a_2], [sentence_b])
                        similarity_comparison.append(second_similarity)
                        if first_similarity + 0.1 < second_similarity > similarity + 0.1 and second_similarity > 0.8:
                            combine_sentences(sentence_a, 1, sentences_a, index, aligned_sentences_a, sentence_b, aligned_sentences_b)
                            final_similarity = second_similarity
                            break
                    except IndexError:
                        pass
                    #Third test (1-3)
                    try:
                        sentence_b_3 = sentences_b[index + 2] 
                        third_similarity = check_similarity([sentence_a], [sentence_b, sentence_b_2, sentence_b_3])
                        similarity_comparison.append(third_similarity)
                        if third_similarity > max(similarity_comparison) and third_similarity > 0.8:
                            combine_sentences(sentence_b, 2, sentences_b, index, aligned_sentences_b, sentence_a, aligned_sentences_a)
                            final_similarity = third_similarity
                            break
                    except IndexError:
                        pass
                    
                    #Fourth test (3-1)
                    try:
                        sentence_a_3 = sentences_a[index + 2]                                 
                        fourth_similarity = check_similarity([sentence_a, sentence_a_2, sentence_a_3], [sentence_b])
                        similarity_comparison.append(fourth_similarity)
                        if fourth_similarity > max(similarity_comparison) and fourth_similarity > 0.8:
                            combine_sentences(sentence_a, 2, sentences_a, index, aligned_sentences_a, sentence_b, aligned_sentences_b)
                            final_similarity = fourth_similarity
                            break
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
                    
                    unique_max_index_list = []
                    [unique_max_index_list.append(i) for i in max_index_list if i not in unique_max_index_list]

                    finished = False
                    goal_similarity = 0.7
                    combined_results = {}
                    
                    for m_index in unique_max_index_list:
                        if m_index == 0:
                            result_check = double_check(sentences_a, sentences_b, index + 1, index + 1)
                            combined_results[0] = result_check + max_values_list[max_index_list.index(0)]
                        if (m_index == 0) and (not result_check or result_check > goal_similarity) and (m_index == max(combined_results, key=combined_results.get)):
                            aligned_sentences_a.append(sentence_a)
                            aligned_sentences_b.append(sentence_b)
                            final_similarity = similarity
                            finished = True
                            break  
                        if m_index == 1:
                            result_check = double_check(sentences_a, sentences_b, index + 1, index + 2)
                            combined_results[1] = result_check + max_values_list[max_index_list.index(1)]
                        if (m_index == 1) and (not result_check or result_check > goal_similarity) and (m_index == max(combined_results, key=combined_results.get)):
                            combine_sentences(sentence_b, 1, sentences_b, index, aligned_sentences_b, sentence_a, aligned_sentences_a)
                            final_similarity = first_similarity
                            finished = True
                            break
                        if m_index == 2:
                            result_check = double_check(sentences_a, sentences_b, index + 2, index + 1)
                            combined_results[2] = result_check + max_values_list[max_index_list.index(2)]
                        if (m_index == 2) and (not result_check or result_check > goal_similarity) and (m_index == max(combined_results, key=combined_results.get)):
                            combine_sentences(sentence_a, 1, sentences_a, index, aligned_sentences_a, sentence_b, aligned_sentences_b)
                            final_similarity = second_similarity
                            finished = True
                            break
                        if m_index == 3:
                            result_check = double_check(sentences_a, sentences_b, index + 1, index + 3)
                            combined_results[3] = result_check + max_values_list[max_index_list.index(3)]
                        if (m_index == 3) and (not result_check or result_check > goal_similarity) and (m_index == max(combined_results, key=combined_results.get)):
                            combine_sentences(sentence_b, 2, sentences_b, index, aligned_sentences_b, sentence_a, aligned_sentences_a)
                            final_similarity = third_similarity
                            finished = True
                            break
                        if m_index == 4:
                            result_check = double_check(sentences_a, sentences_b, index + 3, index + 1)
                            combined_results[4] = result_check + max_values_list[max_index_list.index(4)]
                        if (m_index == 4) and (not result_check or result_check > goal_similarity) and (m_index == max(combined_results, key=combined_results.get)):
                            combine_sentences(sentence_a, 2, sentences_a, index, aligned_sentences_a, sentence_b, aligned_sentences_b)
                            final_similarity = fourth_similarity
                            finished = True
                            break
                        
                        if finished:
                            break
                    if not finished:
                        last_resort_index = max(combined_results, key=lambda k: combined_results[k])
                        if last_resort_index == 1:
                            combine_sentences(sentence_b, 1, sentences_b, index, aligned_sentences_b, sentence_a, aligned_sentences_a)
                            final_similarity = first_similarity
                        elif last_resort_index == 2:
                            combine_sentences(sentence_a, 1, sentences_a, index, aligned_sentences_a, sentence_b, aligned_sentences_b)
                            final_similarity = second_similarity
                        elif last_resort_index == 3:
                            combine_sentences(sentence_b, 2, sentences_b, index, aligned_sentences_b, sentence_a, aligned_sentences_a)
                            final_similarity = third_similarity
                        elif last_resort_index == 4:
                            combine_sentences(sentence_a, 2, sentences_a, index, aligned_sentences_a, sentence_b, aligned_sentences_b)
                            final_similarity = fourth_similarity
                        elif last_resort_index == 0:
                            aligned_sentences_a.append(sentence_a)
                            aligned_sentences_b.append(sentence_b)
                            final_similarity = similarity

                else:
                    aligned_sentences_a.append(sentence_a)
                    aligned_sentences_b.append(sentence_b)
                    final_similarity = similarity
                
                break
            except IndexError:
                run = False
                continue
        
        if run:
            if not len(aligned_sentences_a) == len(aligned_sentences_b):
                if len(aligned_sentences_a) < len(aligned_sentences_b):
                    aligned_sentences_a.append(sentence_a)
                else:
                    aligned_sentences_b.append(sentence_b)
            if not final_similarity:
                final_similarity = 'Empty'
            similarities.append(final_similarity)
            if final_similarity < 0.6:
                warnings.append(index)

            print(index)
            print(aligned_sentences_a[index])
            print(aligned_sentences_b[index])

def create_text_file_from_list(input_list, similarities, warnings, file_path):
    """Create a text file with each item from the input list on a new line."""
    with open(file_path, 'w') as file:
        for index, item in enumerate(input_list):
            warning = '--POTENTIAL WARNING--' if index in warnings else ''
            try:
                file.write(str(item) + f' # {similarities[index]} {warning}' + '\n')
            except IndexError:
                file.write(str(item) + f' # Error {warning}' + '\n')

def store_as_json(output_path, list_a, list_b, similarities, warnings, should_return=False, should_output=True):
    mixed_obj = []
    for index, sentence_a in enumerate(list_a):
        try:
            sentence_b = list_b[index]
            similarity = similarities[index]
            warning = True if index in warnings else False
            mixed_obj.append({
                'language_a': sentence_a,
                'language_b': sentence_b,
                'similarity': similarity,
                'warning': warning
            })
        except IndexError as err:
            print(err)
    python_obj = {
        'text_a': list_a,
        'text_b': list_b,
        'similarities': similarities,
        'warnings': warnings,
        'complete': mixed_obj,
    }
    if should_output:
        out = output_path if output_path else 'unnamed_json_object.json'
        json_data = json.dumps(python_obj)
        with open(out, "w") as json_file:
            json_file.write(json_data)
    if should_return:
        return python_obj

def finished_text_to_json(file1, file2, output):
    sentences_a = []
    sentences_b = []
    with open(file1, 'r') as file:
        for line in file:
            parts = line.split('#', 1)

            sentence = parts[0] if len(parts) > 1 else line
            sentences_a.append(sentence)
    
    with open(file2, 'r') as file:
        for line in file:
            parts = line.split('#', 1)

            sentence = parts[0] if len(parts) > 1 else line
            sentences_b.append(sentence)
    
    json_object = {
        'text_a': sentences_a,
        'text_b': sentences_b,
    }
    json_data = json.dumps(json_object)

    with open(output, 'w') as json_file:
        json_file.write(json_data)

def split_text(textfile1, textfile2, output_option, output_a=None, output_b=None, output_json=None, languages=['en', 'es'],):

    sentences_a = read_sentences_from_file(textfile1, languages[0])
    sentences_b = read_sentences_from_file(textfile2, languages[1])

    aligned_sentences_a = []
    aligned_sentences_b = []
    similarities = []
    warnings = []
    
    align_text(sentences_a, sentences_b, aligned_sentences_a, aligned_sentences_b, similarities, warnings)

    print(len(similarities))
    print(len(warnings))
    print(len(aligned_sentences_a))
    print(len(aligned_sentences_b))
    
    if output_option in [1, 3]:
        create_text_file_from_list(aligned_sentences_a, similarities, warnings, output_a)
        create_text_file_from_list(aligned_sentences_b, similarities, warnings, output_b)
    
    if output_option in [2, 3]:
        store_as_json(output_json, aligned_sentences_a, aligned_sentences_b, similarities, warnings)
    
    if not output_option:
        output = True if output_json else False
        return_object = store_as_json(output_json, aligned_sentences_a, aligned_sentences_b, similarities, warnings, True, output)
        return return_object



