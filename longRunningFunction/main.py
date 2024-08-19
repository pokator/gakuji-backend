# regular function
from jamdict import Jamdict
import jamdict_data
jam = Jamdict(memory_mode=True)

def get_word_info(word):
    result = jam.lookup(word)
    word_info = []
    for entry in result.entries[:3]:  # Include up to 3 entries
        word_info.append(entry.idseq)
    return word_info

def process_tokenized_lines(lines):
    word_dict = {}
    for line in lines:
        for word in line:
            word_info = get_word_info(word)
            if len(word_info) > 0:
                word_dict[word] = word_info
    return word_dict

def process_lines(event, context):
    for record in event['Records']:
        message_body = json.loads(record['body'])
        # Perform the long-running task
        # Update the database
        word_mapping = process_tokenized_lines(tokenized_lines)
        
    return {
        'statusCode': 200,
        'body': json.dumps('Long-running task completed successfully.')
    }
    
    #upon completion update the database with the word_mapping