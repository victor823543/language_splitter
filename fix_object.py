import json


def fix_object(path):
    json_objects = []

    with open(path, 'r') as file:
        object = json.load(file)
        json_objects.append(object)

    timestamps_obj = {}
    latest = 0
    latest_index = 0
    for obj in json_objects:
        stamps_a = obj['timestamps']['timestamps_a']
        stamps_b = obj['timestamps']['timestamps_b']
        
        for i in range(len(stamps_a) + len(stamps_b)):
            timestamp_index = latest_index + i
            if i % 2 == 0:
                n = int(i/2)
                if n:
                    end = (stamps_a[n] - stamps_a[n-1]) + latest
                else:
                    end = stamps_a[n] + latest
            else:
                n = int(((i-1)/2))
                if n:
                    end = (stamps_b[n] - stamps_b[n-1]) + latest
                else:
                    end = stamps_b[n] + latest
            timestamps_obj[timestamp_index] = [latest, end]
            latest = end
        
        latest_index = latest_index + len(stamps_a) + len(stamps_b)
        

    full_object = {
        'text_a': json_objects[0]['text_a'],
        'text_b': json_objects[0]['text_b'],
        'timestamps': timestamps_obj,
    }
    json_out = json.dumps(full_object)

    with open('test_new.json', 'w') as file:
        file.write(json_out)